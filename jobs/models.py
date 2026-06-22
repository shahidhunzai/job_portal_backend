from django.db import models
from departments.models import Department

class Job(models.Model):
    JOB_TYPE_CHOICES = (
        ('onsite', 'On Site'),
        ('remote', 'Remote'),
        ('hybrid', 'Hybrid'),
    )
    
    SELECTION_TYPE_CHOICES = (
        ('test', 'Test'),
        ('interview', 'Interview'),
        ('test_interview', 'Test + Interview'),
    )
    
    STATUS_CHOICES = (
        ('open', 'Open'),
        ('closed', 'Closed'),
    )
    
    department = models.ForeignKey(Department, on_delete=models.CASCADE, related_name='jobs')
    title = models.CharField(max_length=300)
    description = models.TextField()
    required_skills = models.TextField()
    job_type = models.CharField(max_length=20, choices=JOB_TYPE_CHOICES)
    selection_type = models.CharField(max_length=20, choices=SELECTION_TYPE_CHOICES)
    salary_range = models.CharField(max_length=200, null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='open')
    vacancies = models.IntegerField(default=1)
    filled_positions = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.title} - {self.department.name}"
    
    class Meta:
        ordering = ['-created_at']