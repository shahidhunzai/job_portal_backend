from django.db import models
from departments.models import Department

class Chapter(models.Model):
    department = models.ForeignKey(Department, on_delete=models.CASCADE, related_name='chapters')
    name = models.CharField(max_length=300)
    subtitle = models.CharField(max_length=500, null=True, blank=True)
    description = models.TextField()
    image = models.ImageField(upload_to='chapter_images/', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.name} - {self.department.name}"
    
    class Meta:
        ordering = ['-created_at']

class Question(models.Model):
    chapter = models.ForeignKey(Chapter, on_delete=models.CASCADE, related_name='questions')
    question_text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return self.question_text[:100]
    
    class Meta:
        ordering = ['-created_at']

class MCQOption(models.Model):
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='options')
    option_text = models.CharField(max_length=500)
    is_correct = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.option_text} - {'Correct' if self.is_correct else 'Wrong'}"
    
    class Meta:
        ordering = ['id']