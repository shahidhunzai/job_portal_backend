from rest_framework import serializers
from .models import Department
from accounts.models import User
from django.contrib.auth.hashers import make_password

class DepartmentSerializer(serializers.ModelSerializer):
    logo_url = serializers.SerializerMethodField()
    
    class Meta:
        model = Department
        fields = ['id', 'logo', 'logo_url', 'name', 'tagline', 'bio', 'ceo_name', 
                  'email', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_logo_url(self, obj):
        if obj.logo:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.logo.url)
            return obj.logo.url
        return None

class DepartmentCreateSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=True, min_length=8)
    
    class Meta:
        model = Department
        fields = ['logo', 'name', 'tagline', 'bio', 'ceo_name', 'email', 'password']
    
    def validate_email(self, value):
        # Check if email already exists in User model
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return value
    
    def create(self, validated_data):
        password = validated_data.pop('password')
        logo = validated_data.get('logo', None)
        
        # Create user account for department
        user = User.objects.create(
            username=validated_data['email'].split('@')[0],
            email=validated_data['email'],
            user_type='department',
            password=make_password(password),
            first_name=validated_data.get('ceo_name', '').split()[0] if validated_data.get('ceo_name') else '',
            is_active=True,
            profile_picture=logo  # Set the user's profile picture to the department logo
        )
        
        # Create department linked to user
        department = Department.objects.create(
            user=user,
            **validated_data
        )
        
        return department

class DepartmentDetailSerializer(serializers.ModelSerializer):
    logo_url = serializers.SerializerMethodField()
    total_jobs = serializers.SerializerMethodField()
    total_employees = serializers.SerializerMethodField()
    active_jobs = serializers.SerializerMethodField()
    
    class Meta:
        model = Department
        fields = ['id', 'logo', 'logo_url', 'name', 'tagline', 'bio', 'ceo_name', 
                  'email', 'created_at', 'updated_at', 'total_jobs', 'total_employees', 
                  'active_jobs']
    
    def get_logo_url(self, obj):
        if obj.logo:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.logo.url)
            return obj.logo.url
        return None
    
    def get_total_jobs(self, obj):
        return obj.jobs.count()
    
    def get_total_employees(self, obj):
        return obj.employees.count()
    
    def get_active_jobs(self, obj):
        return obj.jobs.filter(status='open').count()