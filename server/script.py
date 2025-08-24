#!/usr/bin/env python3
"""
Simplified Query Processor for Satellite Infrastructure Analysis
Combines query processing and integration into a single file
Returns clean, simple dictionary with essential features only
"""

import json
import re
import os
import time
from datetime import datetime
import google.generativeai as genai

class SimpleQueryProcessor:
    def __init__(self, gemini_api_key: str):
        """Initialize the simplified query processor"""
        self.gemini_api_key = gemini_api_key
        self.gemini_model = self.setup_gemini()
        self.query_counter = 0
        
    def setup_gemini(self):
        """Setup Google Gemini AI"""
        try:
            genai.configure(api_key=self.gemini_api_key)
            
            # Try different Gemini models
            models_to_try = ['gemini-1.5-pro', 'gemini-1.5-flash', 'gemini-1.0-pro', 'gemini-pro']
            
            for model_name in models_to_try:
                try:
                    print(f"   Trying Gemini model: {model_name}...")
                    gemini_model = genai.GenerativeModel(model_name)
                    test_response = gemini_model.generate_content("Hello")
                    print(f"✅ Gemini AI initialized successfully with {model_name}")
                    return gemini_model
                except Exception:
                    continue
            
            print("❌ All Gemini models failed to initialize")
            return None
            
        except Exception as e:
            print(f"❌ Failed to initialize Gemini AI: {e}")
            return None
    
    def process_query(self, user_query: str) -> dict:
        """Main method to process a user query and return simple dictionary"""
        self.query_counter += 1
        
        print(f"🔍 Processing Query: {user_query[:50]}...")
        
        # Extract location
        location = self.extract_location(user_query)
        
        # Classify query
        classification = self.classify_query(user_query)
        
        # Generate simple response
        response = {
            "query_id": f"Q{self.query_counter:04d}",
            "timestamp": datetime.now().isoformat(),
            "user_query": user_query,
            
            "location": {
                "name": location.get("location_name", "Unknown"),
                "type": location.get("location_type", "general"),
                "coordinates": location.get("coordinates", {}),
                "bbox": location.get("bbox", []),
                "confidence": location.get("confidence", 0.0)
            },
            
            "classification": {
                "category": classification.get("query_category", "general"),
                "intent": classification.get("query_intent", "information"),
                "priority": classification.get("priority_level", "medium"),
                "confidence": classification.get("confidence", 0.0)
            },
            
            "analysis": {
                "type": classification.get("analysis_type", "statistical"),
                "metrics": classification.get("specific_metrics", []),
                "requires_comparison": classification.get("requires_comparison", False),
                "estimated_time": "minutes"
            },
            
            "recommendations": self.get_recommendations(classification.get("query_category", "general"))
        }
        
        print(f"✅ Query processed successfully!")
        return response
    
    def extract_location(self, query: str) -> dict:
        """Extract location information from query"""
        if not self.gemini_model:
            return self._fallback_location_extraction(query)
        
        try:
            location_prompt = f"""
            Extract location from this query and return ONLY a JSON object:
            
            QUERY: "{query}"
            
            Return this exact JSON structure:
            {{
                "location_type": "city|coordinates|area|general",
                "location_name": "extracted name or 'General Area'",
                "coordinates": {{"lat": number or null, "lon": number or null}},
                "bbox": [min_lon, min_lat, max_lon, max_lat],
                "confidence": 0.0-1.0
            }}
            
            Rules:
            - If city mentioned: use "city", extract name, set coordinates
            - If coordinates mentioned: use "coordinates", parse lat/lon
            - If no location: use "general", "General Area", null coordinates
            - For cities: generate bbox ±0.1 degrees around coordinates
            - Set confidence: 0.9 for cities, 0.8 for coordinates, 0.3 for general
            
            Return ONLY the JSON, no other text.
            """
            
            response = self.gemini_model.generate_content(location_prompt)
            response_text = response.text.strip()
            
            # Extract JSON
            json_start = response_text.find('{')
            json_end = response_text.rfind('}') + 1
            
            if json_start != -1 and json_end != 0:
                json_str = response_text[json_start:json_end]
                return json.loads(json_str)
            else:
                return self._fallback_location_extraction(query)
                
        except Exception as e:
            print(f"⚠️ Gemini location extraction failed: {e}")
            return self._fallback_location_extraction(query)
    
    def _fallback_location_extraction(self, query: str) -> dict:
        """Fallback location extraction"""
        query_lower = query.lower()
        
        # Major Indian cities
        cities = {
            "delhi": {"lat": 28.6139, "lon": 77.2090},
            "mumbai": {"lat": 19.0760, "lon": 72.8777},
            "bangalore": {"lat": 12.9716, "lon": 77.5946},
            "chennai": {"lat": 13.0827, "lon": 80.2707},
            "kolkata": {"lat": 22.5726, "lon": 88.3639},
            "hyderabad": {"lat": 17.3850, "lon": 78.4867},
            "pune": {"lat": 18.5204, "lon": 73.8567},
            "ahmedabad": {"lat": 23.0225, "lon": 72.5714},
            "jaipur": {"lat": 26.9124, "lon": 75.7873},
            "lucknow": {"lat": 26.8467, "lon": 80.9462}
        }
        
        # Check for coordinates
        coord_match = re.search(r'(\d+\.?\d*)[,\s]+(\d+\.?\d*)', query)
        if coord_match:
            try:
                lat = float(coord_match.group(1))
                lon = float(coord_match.group(2))
                return {
                    "location_type": "coordinates",
                    "location_name": f"Coordinates {lat}, {lon}",
                    "coordinates": {"lat": lat, "lon": lon},
                    "bbox": [lon-0.05, lat-0.05, lon+0.05, lat+0.05],
                    "confidence": 0.8
                }
            except ValueError:
                pass
        
        # Check for cities
        for city, coords in cities.items():
            if city in query_lower:
                return {
                    "location_type": "city",
                    "location_name": city.title(),
                    "coordinates": coords,
                    "bbox": [coords["lon"]-0.1, coords["lat"]-0.1, coords["lon"]+0.1, coords["lat"]+0.1],
                    "confidence": 0.9
                }
        
        # Default
        return {
            "location_type": "general",
            "location_name": "General Area",
            "coordinates": {"lat": None, "lon": None},
            "bbox": [77.0, 28.0, 77.5, 28.5],
            "confidence": 0.3
        }
    
    def classify_query(self, query: str) -> dict:
        """Classify query type and intent"""
        if not self.gemini_model:
            return self._fallback_classification(query)
        
        try:
            classification_prompt = f"""
            Classify this satellite infrastructure query and return ONLY a JSON object:
            
            QUERY: "{query}"
            
            Return this exact JSON structure:
            {{
                "query_category": "infrastructure|quality_of_life|road_conditions|industry|comparison|general",
                "query_intent": "analysis|comparison|prediction|assessment|information",
                "analysis_type": "spatial|statistical|comparative|predictive",
                "priority_level": "high|medium|low",
                "specific_metrics": ["roads", "buildings", "hospitals", "schools", "intersections"],
                "requires_comparison": true|false,
                "confidence": 0.0-1.0
            }}
            
            Categories:
            - infrastructure: roads, buildings, intersections, development
            - quality_of_life: healthcare, education, amenities, living standards
            - road_conditions: traffic, transportation, connectivity, roads
            - industry: commercial, residential, business, industrial
            - comparison: comparing areas, cities, or time periods
            - general: overview, general information, basic analysis
            
            Intents:
            - analysis: detailed examination, deep dive
            - comparison: comparing different things
            - prediction: future outlook, forecasting
            - assessment: current status, evaluation
            - information: basic facts, overview
            
            Set confidence based on how clear the query is (0.9 for very clear, 0.5 for ambiguous)
            
            Return ONLY the JSON, no other text.
            """
            
            response = self.gemini_model.generate_content(classification_prompt)
            response_text = response.text.strip()
            
            # Extract JSON
            json_start = response_text.find('{')
            json_end = response_text.rfind('}') + 1
            
            if json_start != -1 and json_end != 0:
                json_str = response_text[json_start:json_end]
                return json.loads(json_str)
            else:
                return self._fallback_classification(query)
                
        except Exception as e:
            print(f"⚠️ Gemini classification failed: {e}")
            return self._fallback_classification(query)
    
    def _fallback_classification(self, query: str) -> dict:
        """Fallback query classification"""
        query_lower = query.lower()
        
        # Category detection
        if any(word in query_lower for word in ['road', 'building', 'intersection', 'infrastructure', 'development']):
            category = "infrastructure"
        elif any(word in query_lower for word in ['healthcare', 'hospital', 'school', 'education', 'quality', 'life', 'amenity']):
            category = "quality_of_life"
        elif any(word in query_lower for word in ['traffic', 'transportation', 'connectivity', 'road condition']):
            category = "road_conditions"
        elif any(word in query_lower for word in ['commercial', 'residential', 'business', 'industrial', 'store']):
            category = "industry"
        elif any(word in query_lower for word in ['compare', 'versus', 'vs', 'difference', 'between']):
            category = "comparison"
        else:
            category = "general"
        
        # Intent detection
        if any(word in query_lower for word in ['compare', 'versus', 'vs', 'difference']):
            intent = "comparison"
        elif any(word in query_lower for word in ['predict', 'future', 'will', 'going to']):
            intent = "prediction"
        elif any(word in query_lower for word in ['analyze', 'analysis', 'detailed']):
            intent = "analysis"
        elif any(word in query_lower for word in ['assess', 'status', 'current', 'how']):
            intent = "assessment"
        else:
            intent = "information"
        
        # Metrics extraction
        metrics = []
        if any(word in query_lower for word in ['road', 'highway', 'street']):
            metrics.append("roads")
        if any(word in query_lower for word in ['building', 'structure']):
            metrics.append("buildings")
        if any(word in query_lower for word in ['hospital', 'medical', 'clinic']):
            metrics.append("hospitals")
        if any(word in query_lower for word in ['school', 'education', 'university']):
            metrics.append("schools")
        if any(word in query_lower for word in ['intersection', 'crossing', 'junction']):
            metrics.append("intersections")
        
        return {
            "query_category": category,
            "query_intent": intent,
            "analysis_type": "spatial" if "area" in query_lower or "location" in query_lower else "statistical",
            "priority_level": "high" if any(word in query_lower for word in ['urgent', 'important', 'critical']) else "medium",
            "specific_metrics": metrics,
            "requires_comparison": intent == "comparison",
            "confidence": 0.8 if category != "general" else 0.6
        }
    
    def get_recommendations(self, category: str) -> list:
        """Get recommendations based on query category"""
        recommendations = {
            "infrastructure": [
                "Analyze road network density",
                "Assess building infrastructure",
                "Evaluate intersection quality"
            ],
            "quality_of_life": [
                "Check healthcare accessibility",
                "Evaluate educational facilities",
                "Assess amenity coverage"
            ],
            "road_conditions": [
                "Analyze traffic patterns",
                "Assess road connectivity",
                "Evaluate transportation infrastructure"
            ],
            "industry": [
                "Analyze commercial development",
                "Assess residential infrastructure",
                "Evaluate industrial potential"
            ],
            "comparison": [
                "Generate comparative reports",
                "Create visualization charts",
                "Provide ranking analysis"
            ],
            "general": [
                "Conduct comprehensive analysis",
                "Generate overview report",
                "Create development roadmap"
            ]
        }
        
        return recommendations.get(category, ["Analyze the area", "Generate report", "Provide insights"])
    
    def save_response(self, response: dict, output_dir: str = "query_responses") -> str:
        """Save response to JSON file"""
        os.makedirs(output_dir, exist_ok=True)
        
        filename = f"query_response_{response['query_id']}.json"
        filepath = os.path.join(output_dir, filename)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(response, f, indent=2, ensure_ascii=False)
        
        print(f"💾 Response saved to: {filepath}")
        return filepath

def main():
    """Main function to demonstrate the simplified query processor"""
    GEMINI_API_KEY = "AIzaSyD-mkg__8KYzemqcpe1t-nilBMrVELs1Mc"
    
    print("🤖 Simplified Query Processor for Satellite Infrastructure Analysis")
    print("=" * 70)
    
    # Initialize processor
    processor = SimpleQueryProcessor(GEMINI_API_KEY)
    
    if not processor.gemini_model:
        print("⚠️ Warning: Gemini AI not available, using fallback methods")
    
    # Test queries
    test_queries = [
        "What is the infrastructure status in Delhi?",
        "How are the road conditions in Mumbai?",
        "Compare healthcare between Bangalore and Chennai",
        "What will be the quality of life impact in Pune?",
        "Show me building density for coordinates 28.6139°N, 77.2090°E"
    ]
    
    print(f"\n🧪 Testing with {len(test_queries)} example queries...")
    
    for i, query in enumerate(test_queries, 1):
        print(f"\n--- Test Query {i} ---")
        print(f"Query: {query}")
        
        # Process query
        response = processor.process_query(query)
        
        # Save response
        processor.save_response(response)
        
        # Display key results
        print(f"📍 Location: {response['location']['name']} ({response['location']['type']})")
        print(f"🏷️ Category: {response['classification']['category']}")
        print(f"🎯 Intent: {response['classification']['intent']}")
        print(f"📊 Metrics: {', '.join(response['analysis']['metrics'])}")
        print(f"💡 Recommendations: {', '.join(response['recommendations'][:2])}")
    
    print(f"\n✅ Simplified query processor testing completed!")
    print(f"💡 The system now returns clean, simple dictionaries with essential features only.")

if __name__ == "__main__":
    main() 
