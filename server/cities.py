# pip install requests shapely geopandas folium networkx osmnx pandas numpy pillow google-generativeai
import os, io, math, json, time, requests, folium
import numpy as np, pandas as pd
from shapely.geometry import shape, LineString, Point, Polygon
from shapely.ops import unary_union
import geopandas as gpd
import google.generativeai as genai
from geopy.geocoders import Nominatim

def get_city_bounds(city_name, country=None):
    """
    Get min and max latitude and longitude for a given city.
    
    Args:
        city_name (str): Name of the city.
        country (str): Optional, country name to narrow search.

    Returns:
        dict: { 'min_lat': float, 'max_lat': float, 'min_lon': float, 'max_lon': float }
    """
    geolocator = Nominatim(user_agent="geoapi")
    
    # Build query
    query = city_name if not country else f"{city_name}, {country}"
    
    location = geolocator.geocode(query, exactly_one=True)
    
    if not location:
        return {"error": f"City '{city_name}' not found."}
    
    # Fetch detailed data using OSM
    details = geolocator.geocode(query, exactly_one=True, geometry='geojson')
    
    # Get bounding box (min_lat, max_lat, min_lon, max_lon)
    bbox = details.raw.get("boundingbox", None)
    
    if bbox:
        return {
            "min_lat": float(bbox[0]),
            "max_lat": float(bbox[1]),
            "min_lon": float(bbox[2]),
            "max_lon": float(bbox[3])
        }
    else:
        return {"error": "Bounding box not available."}




# ---------- INPUT ----------
bbox = [77.10, 28.55, 77.30, 28.75]  # [min_lon, min_lat, max_lon, max_lat] (example in Delhi)
out_dir = "socio_bbox_outputs"
os.makedirs(out_dir, exist_ok=True)

# Gemini API Key - Replace with your actual key
GEMINI_API_KEY = "AIzaSyB30VO9snpNYH-3i2gyMNC3ZY5fLbAbwJ8"

# ---------- GEMINI AI SETUP ----------
def setup_gemini():
    """Setup Google Gemini AI for analysis"""
    try:
        genai.configure(api_key=GEMINI_API_KEY)
        
        # Try different Gemini models in order of preference
        models_to_try = [
            'gemini-1.5-pro',           # Latest model
            'gemini-1.5-flash',         # Fast model
            'gemini-1.0-pro',           # Previous version
            'gemini-pro'                 # Fallback
        ]
        
        gemini_model = None
        for model_name in models_to_try:
            try:
                print(f"   Trying Gemini model: {model_name}...")
                gemini_model = genai.GenerativeModel(model_name)
                # Test if model works
                test_response = gemini_model.generate_content("Hello")
                print(f"✅ Gemini AI initialized successfully with {model_name}")
                return gemini_model
            except Exception as model_error:
                print(f"   ⚠️ {model_name} failed: {model_error}")
                continue
        
        print("❌ All Gemini models failed to initialize")
        return None
        
    except Exception as e:
        print(f"❌ Failed to initialize Gemini AI: {e}")
        return None

# ---------- HELPERS ----------
def bbox_polygon(b):
    return Polygon([(b[0],b[1]), (b[2],b[1]), (b[2],b[2] if False else b[3]), (b[0],b[3])])

def overpass(query, pause=2.0):
    url = "https://overpass-api.de/api/interpreter"
    r = requests.post(url, data={"data": query}, timeout=120)
    if r.status_code != 200:
        time.sleep(pause)
        r = requests.post(url, data={"data": query}, timeout=120)
    r.raise_for_status()
    return r.json()

def osm_to_gdf(osm_json, geom_types=("way","node","relation")):
    feats = []
    for el in osm_json.get("elements", []):
        if el.get("type") not in geom_types: 
            continue
        tags = el.get("tags", {})
        if el["type"] == "node":
            geom = Point(el["lon"], el["lat"])
        elif el["type"] == "way":
            coords = [(n["lon"], n["lat"]) for n in el["geometry"]]
            geom = LineString(coords)
        else:
            # relations not handled fully; skip for now
            continue
        props = {"id": el["id"], **tags}
        feats.append({"geometry": geom, **props})
    if not feats:
        return gpd.GeoDataFrame(columns=["geometry"], geometry="geometry", crs="EPSG:4326")
    return gpd.GeoDataFrame(feats, geometry="geometry", crs="EPSG:4326")

def length_km(gdf):
    if gdf.empty: return 0.0
    g = gdf.to_crs(3857)
    return g.length.sum() / 1000.0

def point_density_per_km2(gdf, area_km2):
    return 0.0 if gdf.empty or area_km2==0 else len(gdf)/area_km2

def intersection_density_per_km2(roads_gdf, area_km2):
    if roads_gdf.empty or area_km2 == 0:
        return 0.0

    # Crude intersections: count unique vertices occurring in >2 segments
    g = roads_gdf.to_crs(3857)
    pts = []
    for line in g.geometry:
        if line is None:
            continue
        if isinstance(line, LineString):  # Ensure the geometry is a LineString
            for x, y in zip(*line.xy):
                pts.append((round(x, 2), round(y, 2)))
        elif isinstance(line, Polygon):  # Handle Polygon geometries
            for x, y in zip(*line.exterior.xy):
                pts.append((round(x, 2), round(y, 2)))
    
    if not pts:
        return 0.0

    from collections import Counter
    c = Counter(pts)
    inter = sum(1 for k, v in c.items() if v >= 3)
    return inter / area_km2

def norm_clip(x, a, b):
    return max(0.0, min(1.0, (x - a) / (b - a + 1e-9)))

# ---------- ENHANCED ANALYSIS FUNCTIONS ----------
def analyze_infrastructure_percentages(metrics):
    """Analyze infrastructure percentages and development scope"""
    analysis = []
    
    analysis.append("🏗️ INFRASTRUCTURE DEVELOPMENT ANALYSIS")
    analysis.append("=" * 50)
    
    # Road infrastructure analysis
    road_density = metrics['roads_km_per_km2']
    if road_density > 15:
        road_category = "High"
        road_percentage = min(100, (road_density / 25) * 100)
    elif road_density > 8:
        road_category = "Medium"
        road_percentage = min(100, (road_density / 15) * 100)
    else:
        road_category = "Low"
        road_percentage = min(100, (road_density / 8) * 100)
    
    analysis.append(f"\n🛣️ ROAD INFRASTRUCTURE:")
    analysis.append(f"   • Road Density: {road_density:.2f} km/km² ({road_category})")
    analysis.append(f"   • Infrastructure Coverage: {road_percentage:.1f}%")
    analysis.append(f"   • Total Road Length: {metrics['roads_km']:.1f} km")
    
    # Building infrastructure analysis
    building_density = metrics['buildings_per_km2']
    if building_density > 150:
        building_category = "High"
        building_percentage = min(100, (building_density / 300) * 100)
    elif building_density > 80:
        building_category = "Medium"
        building_percentage = min(100, (building_density / 150) * 100)
    else:
        building_category = "Low"
        building_percentage = min(100, (building_density / 80) * 100)
    
    analysis.append(f"\n🏢 BUILDING INFRASTRUCTURE:")
    analysis.append(f"   • Building Density: {building_density:.1f} buildings/km² ({building_category})")
    analysis.append(f"   • Urban Development: {building_percentage:.1f}%")
    analysis.append(f"   • Total Buildings: {metrics['buildings_count']:,}")
    
    # Intersection analysis
    intersection_density = metrics['intersections_per_km2']
    if intersection_density > 20:
        intersection_category = "High"
        intersection_percentage = min(100, (intersection_density / 40) * 100)
    elif intersection_density > 10:
        intersection_category = "Medium"
        intersection_percentage = min(100, (intersection_density / 20) * 100)
    else:
        intersection_category = "Low"
        intersection_percentage = min(100, (intersection_density / 10) * 100)
    
    analysis.append(f"\n🚦 INTERSECTION INFRASTRUCTURE:")
    analysis.append(f"   • Intersection Density: {intersection_density:.1f} intersections/km² ({intersection_category})")
    analysis.append(f"   • Traffic Management: {intersection_percentage:.1f}%")
    
    # Overall infrastructure score
    overall_infra = (road_percentage + building_percentage + intersection_percentage) / 3
    analysis.append(f"\n📊 OVERALL INFRASTRUCTURE DEVELOPMENT:")
    analysis.append(f"   • Comprehensive Score: {overall_infra:.1f}%")
    
    if overall_infra > 70:
        analysis.append("   • Status: Highly Developed")
        analysis.append("   • Development Stage: Mature Infrastructure")
    elif overall_infra > 40:
        analysis.append("   • Status: Moderately Developed")
        analysis.append("   • Development Stage: Growing Infrastructure")
    else:
        analysis.append("   • Status: Developing")
        analysis.append("   • Development Stage: Basic Infrastructure")
    
    return "\n".join(analysis)

def analyze_quality_of_life_impact(metrics):
    """Analyze impact on future quality of life"""
    analysis = []
    
    analysis.append("\n🌟 QUALITY OF LIFE IMPACT ASSESSMENT")
    analysis.append("=" * 50)
    
    # Healthcare accessibility
    hospital_density = metrics['hospitals_per_km2']
    if hospital_density > 0.5:
        healthcare_score = "Excellent"
        healthcare_impact = "High accessibility to medical care"
    elif hospital_density > 0.2:
        healthcare_score = "Good"
        healthcare_impact = "Moderate accessibility to medical care"
    else:
        healthcare_score = "Limited"
        healthcare_impact = "Limited accessibility to medical care"
    
    analysis.append(f"\n🏥 HEALTHCARE ACCESSIBILITY:")
    analysis.append(f"   • Hospital Density: {hospital_density:.4f} hospitals/km²")
    analysis.append(f"   • Healthcare Score: {healthcare_score}")
    analysis.append(f"   • Impact: {healthcare_impact}")
    
    # Education accessibility
    school_density = metrics['schools_per_km2']
    if school_density > 0.4:
        education_score = "Excellent"
        education_impact = "High accessibility to education"
    elif school_density > 0.2:
        education_score = "Good"
        education_impact = "Moderate accessibility to education"
    else:
        education_score = "Limited"
        education_impact = "Limited accessibility to education"
    
    analysis.append(f"\n🎓 EDUCATION ACCESSIBILITY:")
    analysis.append(f"   • School Density: {school_density:.4f} schools/km²")
    analysis.append(f"   • Education Score: {education_score}")
    analysis.append(f"   • Impact: {education_impact}")
    
    # Infrastructure quality
    socio_score = metrics['SocioEconScore']
    if socio_score > 60:
        quality_score = "High"
        quality_impact = "Excellent quality of life with modern amenities"
    elif socio_score > 30:
        quality_score = "Medium"
        quality_impact = "Good quality of life with basic amenities"
    else:
        quality_score = "Basic"
        quality_impact = "Basic quality of life, room for improvement"
    
    analysis.append(f"\n🏠 INFRASTRUCTURE QUALITY:")
    analysis.append(f"   • Socio-Economic Score: {socio_score:.1f}/100")
    analysis.append(f"   • Quality Level: {quality_score}")
    analysis.append(f"   • Impact: {quality_impact}")
    
    # Future quality of life predictions
    analysis.append(f"\n🔮 FUTURE QUALITY OF LIFE PREDICTIONS:")
    
    if socio_score > 60:
        analysis.append("   • High development trajectory")
        analysis.append("   • Expected improvements in services and amenities")
        analysis.append("   • Enhanced community facilities and infrastructure")
        analysis.append("   • Positive impact on daily life and convenience")
    elif socio_score > 30:
        analysis.append("   • Steady development trajectory")
        analysis.append("   • Gradual improvements in infrastructure")
        analysis.append("   • Enhanced accessibility to essential services")
        analysis.append("   • Moderate positive impact on quality of life")
    else:
        analysis.append("   • Development potential identified")
        analysis.append("   • Opportunities for infrastructure improvement")
        analysis.append("   • Potential for enhanced service accessibility")
        analysis.append("   • Foundation for future quality of life improvements")
    
    return "\n".join(analysis)

def analyze_road_conditions(metrics):
    """Analyze road conditions and transportation infrastructure"""
    analysis = []
    
    analysis.append("\n🛣️ ROAD CONDITIONS & TRANSPORTATION ANALYSIS")
    analysis.append("=" * 50)
    
    # Road density analysis
    road_density = metrics['roads_km_per_km2']
    if road_density > 20:
        road_condition = "Excellent"
        road_description = "Comprehensive road network with high connectivity"
        traffic_flow = "High capacity for traffic flow"
    elif road_density > 12:
        road_condition = "Good"
        road_description = "Well-developed road network with good connectivity"
        traffic_flow = "Good capacity for traffic flow"
    elif road_density > 6:
        road_condition = "Moderate"
        road_description = "Moderate road network with basic connectivity"
        traffic_flow = "Moderate capacity for traffic flow"
    else:
        road_condition = "Basic"
        road_description = "Basic road network with limited connectivity"
        traffic_flow = "Limited capacity for traffic flow"
    
    analysis.append(f"\n🛣️ ROAD INFRASTRUCTURE QUALITY:")
    analysis.append(f"   • Road Density: {road_density:.2f} km/km²")
    analysis.append(f"   • Road Condition: {road_condition}")
    analysis.append(f"   • Network Description: {road_description}")
    analysis.append(f"   • Traffic Flow: {traffic_flow}")
    
    # Intersection analysis
    intersection_density = metrics['intersections_per_km2']
    if intersection_density > 20:
        intersection_quality = "Excellent"
        traffic_management = "Advanced traffic management system"
        connectivity = "High connectivity between areas"
    elif intersection_density > 10:
        intersection_quality = "Good"
        traffic_management = "Good traffic management system"
        connectivity = "Good connectivity between areas"
    else:
        intersection_quality = "Basic"
        traffic_management = "Basic traffic management"
        connectivity = "Basic connectivity between areas"
    
    analysis.append(f"\n🚦 TRAFFIC MANAGEMENT:")
    analysis.append(f"   • Intersection Density: {intersection_density:.1f} intersections/km²")
    analysis.append(f"   • Intersection Quality: {intersection_quality}")
    analysis.append(f"   • Traffic Management: {traffic_management}")
    analysis.append(f"   • Area Connectivity: {connectivity}")
    
    # Transportation accessibility
    analysis.append(f"\n🚌 TRANSPORTATION ACCESSIBILITY:")
    
    if road_density > 15 and intersection_density > 15:
        accessibility = "Excellent"
        mobility = "High mobility and accessibility"
        public_transport = "Ideal for public transportation development"
    elif road_density > 10 and intersection_density > 8:
        accessibility = "Good"
        mobility = "Good mobility and accessibility"
        public_transport = "Suitable for public transportation"
    else:
        accessibility = "Limited"
        mobility = "Limited mobility and accessibility"
        public_transport = "Basic transportation infrastructure"
    
    analysis.append(f"   • Accessibility Level: {accessibility}")
    analysis.append(f"   • Mobility Assessment: {mobility}")
    analysis.append(f"   • Public Transport Potential: {public_transport}")
    
    # Road maintenance and development needs
    analysis.append(f"\n🔧 ROAD DEVELOPMENT NEEDS:")
    
    if road_density < 10:
        analysis.append("   • High priority for road network expansion")
        analysis.append("   • Need for additional arterial and collector roads")
        analysis.append("   • Potential for improved connectivity")
    elif road_density < 15:
        analysis.append("   • Medium priority for road improvements")
        analysis.append("   • Need for road quality enhancements")
        analysis.append("   • Potential for traffic flow optimization")
    else:
        analysis.append("   • Low priority for major road development")
        analysis.append("   • Focus on maintenance and optimization")
        analysis.append("   • Potential for advanced traffic management")
    
    return "\n".join(analysis)

def analyze_industry_availability(metrics):
    """Analyze industry availability and commercial infrastructure"""
    analysis = []
    
    analysis.append("\n🏪 INDUSTRY & COMMERCIAL INFRASTRUCTURE ANALYSIS")
    analysis.append("=" * 50)
    
    # Building density analysis for commercial potential
    building_density = metrics['buildings_per_km2']
    if building_density > 150:
        commercial_potential = "High"
        commercial_description = "Dense urban area with high commercial activity"
        market_size = "Large market with high consumer density"
    elif building_density > 80:
        commercial_potential = "Medium"
        commercial_description = "Moderate urban area with good commercial potential"
        market_size = "Medium market with moderate consumer density"
    else:
        commercial_potential = "Low"
        commercial_description = "Sparse area with limited commercial activity"
        market_size = "Small market with low consumer density"
    
    analysis.append(f"\n🏪 COMMERCIAL INFRASTRUCTURE:")
    analysis.append(f"   • Building Density: {building_density:.1f} buildings/km²")
    analysis.append(f"   • Commercial Potential: {commercial_potential}")
    analysis.append(f"   • Market Description: {commercial_description}")
    analysis.append(f"   • Market Size: {market_size}")
    
    # Healthcare infrastructure analysis
    hospital_density = metrics['hospitals_per_km2']
    if hospital_density > 0.5:
        healthcare_availability = "Excellent"
        healthcare_coverage = "Comprehensive healthcare coverage"
        medical_accessibility = "High accessibility to medical services"
    elif hospital_density > 0.2:
        healthcare_availability = "Good"
        healthcare_coverage = "Good healthcare coverage"
        medical_accessibility = "Good accessibility to medical services"
    else:
        healthcare_availability = "Limited"
        healthcare_coverage = "Limited healthcare coverage"
        medical_accessibility = "Limited accessibility to medical services"
    
    analysis.append(f"\n🏥 HEALTHCARE INFRASTRUCTURE:")
    analysis.append(f"   • Hospital Density: {hospital_density:.4f} hospitals/km²")
    analysis.append(f"   • Healthcare Availability: {healthcare_availability}")
    analysis.append(f"   • Coverage Level: {healthcare_coverage}")
    analysis.append(f"   • Medical Accessibility: {medical_accessibility}")
    
    # Education infrastructure analysis
    school_density = metrics['schools_per_km2']
    if school_density > 0.4:
        education_availability = "Excellent"
        education_coverage = "Comprehensive educational coverage"
        learning_accessibility = "High accessibility to educational services"
    elif school_density > 0.2:
        education_availability = "Good"
        education_coverage = "Good educational coverage"
        learning_accessibility = "Good accessibility to educational services"
    else:
        education_availability = "Limited"
        education_coverage = "Limited educational coverage"
        learning_accessibility = "Limited accessibility to educational services"
    
    analysis.append(f"\n🎓 EDUCATIONAL INFRASTRUCTURE:")
    analysis.append(f"   • School Density: {school_density:.4f} schools/km²")
    analysis.append(f"   • Education Availability: {education_availability}")
    analysis.append(f"   • Coverage Level: {education_coverage}")
    analysis.append(f"   • Learning Accessibility: {learning_accessibility}")
    
    # Residential infrastructure analysis
    if building_density > 100:
        residential_availability = "High"
        residential_density = "High residential density"
        community_size = "Large community with diverse housing options"
    elif building_density > 50:
        residential_availability = "Medium"
        residential_density = "Medium residential density"
        community_size = "Medium community with good housing options"
    else:
        residential_availability = "Low"
        residential_density = "Low residential density"
        community_size = "Small community with limited housing options"
    
    analysis.append(f"\n🏠 RESIDENTIAL INFRASTRUCTURE:")
    analysis.append(f"   • Residential Availability: {residential_availability}")
    analysis.append(f"   • Density Level: {residential_density}")
    analysis.append(f"   • Community Size: {community_size}")
    
    # Industry development recommendations
    analysis.append(f"\n🏭 INDUSTRY DEVELOPMENT RECOMMENDATIONS:")
    
    if commercial_potential == "High":
        analysis.append("   • Ideal for retail and service industry development")
        analysis.append("   • High potential for commercial real estate")
        analysis.append("   • Suitable for entertainment and hospitality sectors")
    elif commercial_potential == "Medium":
        analysis.append("   • Good potential for local business development")
        analysis.append("   • Moderate commercial real estate opportunities")
        analysis.append("   • Suitable for community services and retail")
    else:
        analysis.append("   • Limited commercial development potential")
        analysis.append("   • Focus on essential services and local businesses")
        analysis.append("   • Potential for specialized or niche markets")
    
    return "\n".join(analysis)

def generate_gemini_analysis(metrics, gemini_model):
    """Generate comprehensive analysis using Gemini AI"""
    if gemini_model is None:
        return "Gemini AI not available - using enhanced text analysis instead."
    
    try:
        # Create comprehensive prompt for Gemini AI
        prompt = f"""
        You are an urban planning expert analyzing satellite data for infrastructure development. 
        
        Analyze this area based on the following metrics and provide insights in simple, engaging language:
        
        AREA OVERVIEW:
        - Geographic Area: {metrics['area_km2']:.1f} km²
        - Location: Bounding box coordinates {metrics['bbox']}
        
        INFRASTRUCTURE METRICS:
        - Road Density: {metrics['roads_km_per_km2']:.2f} km/km²
        - Total Roads: {metrics['roads_km']:.1f} km
        - Building Count: {metrics['buildings_count']:,}
        - Building Density: {metrics['buildings_per_km2']:.1f} buildings/km²
        - Intersection Density: {metrics['intersections_per_km2']:.1f} intersections/km²
        
        SERVICE AVAILABILITY:
        - Hospital Density: {metrics['hospitals_per_km2']:.4f} hospitals/km²
        - School Density: {metrics['schools_per_km2']:.4f} schools/km²
        - Overall Socio-Economic Score: {metrics['SocioEconScore']:.1f}/100
        
        Please provide a comprehensive analysis covering:
        
        1. **Infrastructure Development Status**: What does this data tell us about the area's development level?
        2. **Quality of Life Assessment**: How do these metrics impact daily life and future prospects?
        3. **Road Network Analysis**: What are the strengths and areas for improvement in transportation?
        4. **Commercial & Industrial Potential**: What opportunities exist for business development?
        5. **Community Services**: How well-served is the area in terms of healthcare, education, and amenities?
        6. **Future Development Recommendations**: What should be prioritized for improvement?
        
        Write as if you're explaining to a community leader or urban planner. Use simple language, avoid jargon, and make it engaging and actionable.
        Focus on practical implications and clear recommendations.
        """
        
        # Generate analysis
        response = gemini_model.generate_content(prompt)
        return response.text
        
    except Exception as e:
        print(f"⚠️ Gemini AI analysis failed: {e}")
        return "Gemini AI analysis unavailable - using enhanced text analysis instead."

data = {}

cities = ["Pune", "Mumbai", "Delhi", "Bangalore", "Chennai", "Kolkata", "Hyderabad", "Ahmedabad", "Jaipur", "Lucknow", "Surat", "Kanpur", "Nagpur", "Indore", "Thane", "Bhopal", "Visakhapatnam", "Patna", "Vadodara", "Ghaziabad", "Ludhiana", "Agra", "Nashik", "Faridabad", "Meerut", "Rajkot", "Kalyan-Dombivali", "Vasai-Virar", "Varanasi", "Srinagar", "Aurangabad", "Dhanbad", "Amritsar", "Allahabad", "Ranchi", "Howrah", "Coimbatore", "Jabalpur", "Gwalior", "Vijayawada", "Jodhpur", "Madurai", "Raipur", "Kota", "Guwahati", "Chandigarh", "Solapur", "Hubli-Dharwad", "Mysore", "Tiruchirappalli"]
for city in cities:
    bounds = get_city_bounds(city, "India")
    bbox = [bounds['min_lon'] , bounds['min_lat'] , bounds['max_lon'] , bounds['max_lat']]
    poly = bbox_polygon(bbox)
    aoi = gpd.GeoDataFrame([{"geometry": poly}], crs="EPSG:4326")
    area_km2 = aoi.to_crs(3857).area.iloc[0] / 1e6

    # ---------- OSM QUERIES ----------
    # 1) Roads (highways)  2) Buildings  3) Amenities (hospitals, schools, stations, stops)
    minlon, minlat, maxlon, maxlat = bbox
    Q_BASE = f"({minlat},{minlon},{maxlat},{maxlon})"

    Q_ROADS = f"""
    [out:json][timeout:60];
    way{Q_BASE}[highway];
    out geom;
    """
    Q_BUILD = f"""
    [out:json][timeout:60];
    way{Q_BASE}[building];
    out geom;
    """
    Q_AMEN = f"""
    [out:json][timeout:60];
    (
    node{Q_BASE}[amenity=hospital];
    node{Q_BASE}[amenity=clinic];
    node{Q_BASE}[amenity=school];
    node{Q_BASE}[amenity=university];
    node{Q_BASE}[public_transport=station];
    node{Q_BASE}[highway=bus_stop];
    );
    out body;
    """

    roads = osm_to_gdf(overpass(Q_ROADS))
    build = osm_to_gdf(overpass(Q_BUILD))
    amen  = osm_to_gdf(overpass(Q_AMEN), geom_types=("node",))

    # clip to bbox (robust)
    roads = gpd.overlay(roads, aoi, how="intersection") if not roads.empty else roads
    build = gpd.overlay(build, aoi, how="intersection") if not build.empty else build
    amen  = gpd.overlay(amen,  aoi, how="intersection") if not amen.empty  else amen


    # ---------- METRICS ----------
    road_km = length_km(roads)
    road_km_per_km2 = 0.0 if area_km2==0 else road_km / area_km2
    bldg_count = 0 if build.empty else len(build)
    bldg_per_km2 = 0.0 if area_km2==0 else bldg_count / area_km2
    intxn_per_km2 = intersection_density_per_km2(roads, area_km2)

    hospitals = amen[amen.get("amenity")=="hospital"] if not amen.empty else amen
    schools   = amen[amen.get("amenity")=="school"] if not amen.empty else amen

    hosp_per_km2 = point_density_per_km2(hospitals, area_km2)
    school_per_km2= point_density_per_km2(schools, area_km2)

    # TODO (optional): fetch VIIRS nightlights & WorldPop/HRSL population for bbox and add here.

    # ---------- DERIVED INDICES ----------
    infra   = 0.5*norm_clip(road_km_per_km2, 0,10) + 0.5*norm_clip(intxn_per_km2, 0,200)
    access  = 0.5*norm_clip(hosp_per_km2, 0,5) + 0.5*norm_clip(school_per_km2, 0,8)
    activity= 0.0  # replace with normed VIIRS if added
    green   = 0.0  # replace with green_ratio if added

    socio_score = 100.0*(0.35*infra + 0.35*access + 0.20*activity + 0.10*green)

    # ---------- MAP IMAGE ----------
    center_lat = (minlat+maxlat)/2
    center_lon = (minlon+maxlon)/2
    m = folium.Map(location=[center_lat, center_lon], zoom_start=14, tiles="OpenStreetMap")
    folium.Rectangle(bounds=[[minlat,minlon],[maxlat,maxlon]], color="#FF0000", fill=False).add_to(m)

    # overlay roads/buildings/amenities
    if not roads.empty:
        for _, r in roads.iterrows():
            try:
                coords = list(r.geometry.coords)
                folium.PolyLine([(y,x) for x,y in coords], weight=2).add_to(m)
            except Exception:
                pass
    if not build.empty:
        # draw building centroids lightly to avoid heavy polygons
        for _, b in build.iterrows():
            try:
                c = b.geometry.centroid
                folium.CircleMarker([c.y, c.x], radius=1).add_to(m)
            except Exception:
                pass
    if not amen.empty:
        for _, a in amen.iterrows():
            p = a.geometry
            folium.CircleMarker([p.y, p.x], radius=3).add_to(m)

    map_html = os.path.join(out_dir, "bbox_map.html")
    m.save(map_html)

    # ---------- ENHANCED ANALYSIS ----------
    print("\n🤖 Initializing Gemini AI for enhanced analysis...")
    gemini_model = setup_gemini()

    # Create metrics dictionary
    metrics = {
        "bbox": bbox,
        "area_km2": round(area_km2, 3),
        "roads_km": round(road_km, 3),
        "roads_km_per_km2": round(road_km_per_km2, 3),
        "buildings_count": int(bldg_count),
        "buildings_per_km2": round(bldg_per_km2, 3),
        "intersections_per_km2": round(intxn_per_km2, 3),
        "hospitals_per_km2": round(hosp_per_km2, 4),
        "schools_per_km2": round(school_per_km2, 4),
        "SocioEconScore": round(socio_score, 1),
        "map_file": map_html
    }

    data[city] = metrics
print(data)

