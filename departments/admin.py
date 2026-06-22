from django.contrib import admin
from .models import Department

@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ['name', 'ceo_name', 'email', 'created_at']
    search_fields = ['name', 'ceo_name', 'email', 'tagline']
    readonly_fields = ['created_at', 'updated_at']
    list_filter = ['created_at']