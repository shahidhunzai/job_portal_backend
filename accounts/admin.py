from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, Resume, ActivityLog

@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = ['username', 'email', 'user_type', 'first_name', 'last_name', 'is_staff']
    list_filter = ['user_type', 'is_staff', 'is_superuser', 'is_active']
    search_fields = ['username', 'email', 'first_name', 'last_name', 'cnic']
    
    fieldsets = UserAdmin.fieldsets + (
        ('Custom Fields', {
            'fields': ('user_type', 'profile_picture', 'father_name', 'address', 
                      'cnic', 'current_job', 'experience', 'education')
        }),
    )
    
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Custom Fields', {
            'fields': ('user_type', 'profile_picture', 'father_name', 'address', 
                      'cnic', 'current_job', 'experience', 'education')
        }),
    )

@admin.register(Resume)
class ResumeAdmin(admin.ModelAdmin):
    list_display = ['user', 'title', 'is_primary', 'created_at']
    list_filter = ['is_primary', 'created_at']
    search_fields = ['user__username', 'title', 'cnic']
    readonly_fields = ['created_at', 'updated_at']

@admin.register(ActivityLog)
class ActivityLogAdmin(admin.ModelAdmin):
    list_display = ['user', 'action', 'ip_address', 'timestamp']
    list_filter = ['timestamp', 'action']
    search_fields = ['user__username', 'action', 'details']
    readonly_fields = ['timestamp']