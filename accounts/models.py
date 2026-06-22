from django.contrib.auth.models import AbstractUser
from django.db import models

class User(AbstractUser):
    USER_TYPE_CHOICES = (
        ('super_admin', 'Super Admin'),
        ('department', 'Department'),
        ('job_seeker', 'Job Seeker'),
    )
    
    user_type = models.CharField(max_length=20, choices=USER_TYPE_CHOICES)
    profile_picture = models.ImageField(upload_to='profile_pictures/', null=True, blank=True)
    father_name = models.CharField(max_length=200, null=True, blank=True)
    address = models.TextField(null=True, blank=True)
    cnic = models.CharField(max_length=15, null=True, blank=True, unique=True)
    current_job = models.CharField(max_length=200, null=True, blank=True)
    experience = models.TextField(null=True, blank=True)
    education = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.username} - {self.user_type}"

class Resume(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='resumes')
    title = models.CharField(max_length=200)
    father_name = models.CharField(max_length=200)
    address = models.TextField()
    cnic = models.CharField(max_length=15)
    current_job = models.CharField(max_length=200, null=True, blank=True)
    experience = models.TextField()
    education = models.TextField()
    is_primary = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.user.username} - {self.title}"
    
    class Meta:
        ordering = ['-created_at']

class ActivityLog(models.Model):
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    action = models.CharField(max_length=255)
    details = models.TextField(null=True, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.user.username if self.user else 'Unknown'} - {self.action} - {self.timestamp}"
    
    class Meta:
        ordering = ['-timestamp']