from django.urls import include, path
from .views import raw_upload

urlpatterns = [
    path('upload_raw/', raw_upload, name='raw-upload'),
]
