from django.db import models
from accounts.models import User, Resume
from jobs.models import Job
from tests.models import Chapter

class Application(models.Model):
    STATUS_CHOICES = (
        ('applied', 'Applied'),
        ('test_assigned', 'Test Assigned'),
        ('test_completed', 'Test Completed'),
        ('test_passed', 'Test Passed'),
        ('test_failed', 'Test Failed'),
        ('interview_scheduled', 'Interview Scheduled'),
        ('interview_completed', 'Interview Completed'),
        ('waiting', 'Waiting'),
        ('notice_period', 'Notice Period'),
        ('hired', 'Hired'),
        ('rejected', 'Rejected'),
    )
    
    job = models.ForeignKey(Job, on_delete=models.CASCADE, related_name='applications')
    applicant = models.ForeignKey(User, on_delete=models.CASCADE, related_name='applications')
    resume = models.ForeignKey(Resume, on_delete=models.SET_NULL, null=True)
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default='applied')
    rejection_reason = models.TextField(null=True, blank=True)
    applied_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.applicant.username} - {self.job.title} - {self.status}"
    
    class Meta:
        ordering = ['-applied_at']
        unique_together = ['job', 'applicant']

class TestAssignment(models.Model):
    application = models.OneToOneField(Application, on_delete=models.CASCADE, related_name='test_assignment')
    chapter = models.ForeignKey(Chapter, on_delete=models.CASCADE)
    deadline = models.DateTimeField()
    pass_percentage = models.IntegerField(default=70)
    assigned_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.application.applicant.username} - {self.chapter.name}"

class TestResult(models.Model):
    test_assignment = models.OneToOneField(TestAssignment, on_delete=models.CASCADE, related_name='result')
    score = models.FloatField()
    total_questions = models.IntegerField()
    correct_answers = models.IntegerField()
    percentage = models.FloatField()
    passed = models.BooleanField()
    completed_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.test_assignment.application.applicant.username} - {self.percentage}%"

class TestAnswer(models.Model):
    test_result = models.ForeignKey(TestResult, on_delete=models.CASCADE, related_name='answers')
    question = models.ForeignKey('tests.Question', on_delete=models.CASCADE)
    selected_options = models.ManyToManyField('tests.MCQOption')
    is_correct = models.BooleanField()
    
    def __str__(self):
        return f"{self.test_result.test_assignment.application.applicant.username} - Q: {self.question.id}"

class Interview(models.Model):
    application = models.OneToOneField(Application, on_delete=models.CASCADE, related_name='interview')
    interview_link = models.URLField()
    interview_datetime = models.DateTimeField()
    message = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.application.applicant.username} - {self.interview_datetime}"