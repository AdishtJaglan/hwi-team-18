from rest_framework import viewsets, permissions
from .models import SatelliteImage
from .serializers import SatelliteImageSerializer

class SatelliteImageViewSet(viewsets.ModelViewSet):
    queryset = SatelliteImage.objects.all()
    serializer_class = SatelliteImageSerializer
    permission_classes = [permissions.AllowAny]
