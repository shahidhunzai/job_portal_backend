from django.db import models
from accounts.models import User

class Department(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='department')
    logo = models.ImageField(upload_to='department_logos/')
    name = models.CharField(max_length=200)
    tagline = models.CharField(max_length=300, null=True, blank=True)
    bio = models.TextField()
    ceo_name = models.CharField(max_length=200)
    email = models.EmailField(unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return self.name
    
    class Meta:
        ordering = ['-created_at']