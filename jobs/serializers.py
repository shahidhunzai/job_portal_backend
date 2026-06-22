from rest_framework import serializers
from .models import Job
from departments.serializers import DepartmentSerializer

class JobSerializer(serializers.ModelSerializer):
    department_name = serializers.CharField(source='department.name', read_only=True)
    department_logo = serializers.SerializerMethodField()
    
    class Meta:
        model = Job
        fields = [
            'id', 'department', 'department_name', 'department_logo',
            'title', 'description', 'required_skills', 'job_type', 
            'selection_type', 'salary_range', 'status', 'vacancies', 
            'filled_positions', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_department_logo(self, obj):
        if obj.department.logo:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.department.logo.url)
            return obj.department.logo.url
        return None

class JobDetailSerializer(serializers.ModelSerializer):
    department_name = serializers.CharField(source='department.name', read_only=True)
    department_logo = serializers.SerializerMethodField()
    department_tagline = serializers.CharField(source='department.tagline', read_only=True)
    department_bio = serializers.CharField(source='department.bio', read_only=True)
    department_ceo = serializers.CharField(source='department.ceo_name', read_only=True)
    department_email = serializers.EmailField(source='department.email', read_only=True)
    total_applications = serializers.SerializerMethodField()
    
    class Meta:
        model = Job
        fields = [
            'id', 'department', 'department_name', 'department_logo',
            'department_tagline', 'department_bio', 'department_ceo', 'department_email',
            'title', 'description', 'required_skills', 'job_type', 
            'selection_type', 'salary_range', 'status', 'vacancies', 
            'filled_positions', 'total_applications', 'created_at', 'updated_at'
        ]
    
    def get_department_logo(self, obj):
        if obj.department.logo:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.department.logo.url)
            return obj.department.logo.url
        return None
    
    def get_total_applications(self, obj):
        return obj.applications.count()

class JobCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Job
        fields = [
            'title', 'description', 'required_skills', 'job_type', 
            'selection_type', 'salary_range', 'vacancies'
        ]
    
    def validate_vacancies(self, value):
        if value < 1:
            raise serializers.ValidationError("Vacancies must be at least 1")
        return value