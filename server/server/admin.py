from django.contrib import admin
from .models import SatelliteImage

@admin.register(SatelliteImage)
class SatelliteImageAdmin(admin.ModelAdmin):
    list_display = ('id', 'location', 'sublocation', 'image', 'uploaded_at')
    list_filter = ('location', 'sublocation', 'uploaded_at')
    search_fields = ('location', 'sublocation')
