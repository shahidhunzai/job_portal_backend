from django.contrib import admin
from .models import Employee

@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    list_display = ['user', 'designation', 'department', 'salary', 'joining_date']
    list_filter = ['department', 'joining_date', 'created_at']
    search_fields = ['user__username', 'designation', 'department__name']
    readonly_fields = ['created_at']