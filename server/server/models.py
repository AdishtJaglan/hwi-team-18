import os
import uuid
from django.db import models
from django.utils.text import slugify

def satellite_image_upload_to(instance, filename):
    """
    Build path: <location>/<sublocation>/<slugified-filename>-<short-uuid>.<ext>
    Falls back to 'unknown' / 'general' when fields are empty.
    """
    name, ext = os.path.splitext(filename)
    uid = uuid.uuid4().hex[:8]
    location = slugify(instance.location or 'unknown')
    sub = slugify(instance.sublocation) if instance.sublocation else 'general'
    safe_name = slugify(name)[:50] or 'image'
    final_name = f"{safe_name}-{uid}{ext}"
    return os.path.join(location, sub, final_name)

class SatelliteImage(models.Model):
    location = models.CharField(max_length=120, help_text="City / major place (e.g. New Delhi)")
    sublocation = models.CharField(max_length=120, blank=True, null=True, help_text="Optional finer location (e.g. north)")
    image = models.ImageField(upload_to=satellite_image_upload_to)
    captured_at = models.DateTimeField(blank=True, null=True, help_text="When the satellite captured the image")
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-uploaded_at']

    def __str__(self):
        return f"{self.location} / {self.sublocation or 'general'} — {self.id}"
