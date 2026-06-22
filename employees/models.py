from django.db import models
from accounts.models import User
from departments.models import Department
from jobs.models import Job

class Employee(models.Model):
    department = models.ForeignKey(Department, on_delete=models.CASCADE, related_name='employees')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='employee_profile', null=True, blank=True)
    
    # Direct employee fields (no user account needed)
    name = models.CharField(max_length=255)
    father_name = models.CharField(max_length=255, blank=True, null=True)
    cnic = models.CharField(max_length=15, blank=True, null=True)
    profile_picture = models.ImageField(upload_to='employee_pictures/', blank=True, null=True)
    
    # Employment details
    job = models.ForeignKey(Job, on_delete=models.SET_NULL, null=True, blank=True, related_name='employees')
    designation = models.CharField(max_length=255)
    salary = models.DecimalField(max_digits=10, decimal_places=2)
    joining_date = models.DateField()
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-joining_date']
    
    def __str__(self):
        return f"{self.name} - {self.designation}"