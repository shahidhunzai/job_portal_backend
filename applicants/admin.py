from django.contrib import admin
from .models import Application, TestAssignment, TestResult, TestAnswer, Interview

@admin.register(Application)
class ApplicationAdmin(admin.ModelAdmin):
    list_display = ['applicant', 'job', 'status', 'applied_at']
    list_filter = ['status', 'applied_at', 'job__department']
    search_fields = ['applicant__username', 'job__title', 'job__department__name']
    readonly_fields = ['applied_at', 'updated_at']

@admin.register(TestAssignment)
class TestAssignmentAdmin(admin.ModelAdmin):
    list_display = ['application', 'chapter', 'deadline', 'pass_percentage', 'assigned_at']
    list_filter = ['assigned_at', 'deadline']
    search_fields = ['application__applicant__username', 'chapter__name']
    readonly_fields = ['assigned_at']

@admin.register(TestResult)
class TestResultAdmin(admin.ModelAdmin):
    list_display = ['test_assignment', 'percentage', 'passed', 'completed_at']
    list_filter = ['passed', 'completed_at']
    search_fields = ['test_assignment__application__applicant__username']
    readonly_fields = ['completed_at']

@admin.register(TestAnswer)
class TestAnswerAdmin(admin.ModelAdmin):
    list_display = ['test_result', 'question', 'is_correct']
    list_filter = ['is_correct']
    search_fields = ['test_result__test_assignment__application__applicant__username']

@admin.register(Interview)
class InterviewAdmin(admin.ModelAdmin):
    list_display = ['application', 'interview_datetime', 'created_at']
    list_filter = ['interview_datetime', 'created_at']
    search_fields = ['application__applicant__username', 'application__job__title']
    readonly_fields = ['created_at']