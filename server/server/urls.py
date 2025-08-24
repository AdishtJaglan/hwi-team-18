from django.urls import include, path
from .views import raw_upload, extract_location_and_fetch_images, query_insight

urlpatterns = [
    path('upload_raw/', raw_upload, name='raw-upload'),
    path('extract_and_fetch/', extract_location_and_fetch_images, name='extract-and-fetch'),
    path('send_query/', query_insight, name='query-insight')
]
