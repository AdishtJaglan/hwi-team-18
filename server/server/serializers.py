from rest_framework import serializers
from .models import SatelliteImage

class SatelliteImageSerializer(serializers.ModelSerializer):
    image_url = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = SatelliteImage
        fields = ['id', 'location', 'sublocation', 'image', 'image_url', 'captured_at', 'uploaded_at']
        read_only_fields = ['id', 'image_url', 'uploaded_at']

    def get_image_url(self, obj):
        request = self.context.get('request')
        if obj.image and request:
            return request.build_absolute_uri(obj.image.url)
        if obj.image:
            return obj.image.url
        return None
