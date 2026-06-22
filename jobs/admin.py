from django.contrib import admin
from .models import Job

@admin.register(Job)
class JobAdmin(admin.ModelAdmin):
    list_display = ['title', 'department', 'job_type', 'selection_type', 'status', 'vacancies', 'filled_positions', 'created_at']
    list_filter = ['status', 'job_type', 'selection_type', 'created_at']
    search_fields = ['title', 'description', 'required_skills', 'department__name']
    readonly_fields = ['created_at', 'updated_at']