from django.urls import include, path
from rest_framework.routers import DefaultRouter
from .views import SatelliteImageViewSet

router = DefaultRouter()
router.register(r'images', SatelliteImageViewSet, basename='satelliteimage')

urlpatterns = [
    path('', include(router.urls)),
]
