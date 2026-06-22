from rest_framework import serializers
from .models import Employee
from accounts.models import User
from departments.models import Department


class EmployeeSerializer(serializers.ModelSerializer):
    """
    Serializer for listing employees with basic info
    """
    user_username = serializers.CharField(source='user.username', read_only=True)
    user_email = serializers.CharField(source='user.email', read_only=True)
    user_profile_picture = serializers.SerializerMethodField()
    department_name = serializers.CharField(source='department.name', read_only=True)
    department_logo = serializers.SerializerMethodField()
    job_title = serializers.CharField(source='job.title', read_only=True, allow_null=True)
    
    class Meta:
        model = Employee
        fields = [
            'id', 'user', 'user_username', 'user_email', 'user_profile_picture',
            'department', 'department_name', 'department_logo',
            'job', 'job_title', 'designation', 'salary', 'joining_date', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']
    
    def get_user_profile_picture(self, obj):
        if obj.user.profile_picture:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.user.profile_picture.url)
            return obj.user.profile_picture.url
        return None
    
    def get_department_logo(self, obj):
        if obj.department.logo:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.department.logo.url)
            return obj.department.logo.url
        return None


class EmployeeDetailSerializer(serializers.ModelSerializer):
    """
    Detailed serializer for individual employee view
    """
    user_details = serializers.SerializerMethodField()
    department_name = serializers.CharField(source='department.name', read_only=True)
    department_logo = serializers.SerializerMethodField()
    job_title = serializers.CharField(source='job.title', read_only=True, allow_null=True)
    
    class Meta:
        model = Employee
        fields = [
            'id', 'user_details', 'department', 'department_name', 'department_logo',
            'job', 'job_title', 'designation', 'salary', 'joining_date', 'created_at'
        ]
    
    def get_user_details(self, obj):
        request = self.context.get('request')
        return {
            'id': obj.user.id,
            'username': obj.user.username,
            'email': obj.user.email,
            'first_name': obj.user.first_name,
            'last_name': obj.user.last_name,
            'profile_picture': request.build_absolute_uri(obj.user.profile_picture.url) if obj.user.profile_picture and request else None,
            'father_name': obj.user.father_name,
            'address': obj.user.address,
            'cnic': obj.user.cnic,
            'current_job': obj.user.current_job,
            'experience': obj.user.experience,
            'education': obj.user.education,
        }
    
    def get_department_logo(self, obj):
        if obj.department.logo:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.department.logo.url)
            return obj.department.logo.url
        return None


class EmployeeCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating new employees
    """
    class Meta:
        model = Employee
        fields = ['user', 'job', 'designation', 'salary', 'joining_date']
    
    def validate_user(self, value):
        # Check if user is a job seeker
        if value.user_type != 'job_seeker':
            raise serializers.ValidationError("Only job seekers can be employees")
        
        # Check if user is already an employee in any department
        if Employee.objects.filter(user=value).exists():
            raise serializers.ValidationError("This user is already an employee")
        
        return value


class EmployeeUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer for updating employee information
    """
    class Meta:
        model = Employee
        fields = ['designation', 'salary', 'joining_date']



from rest_framework import serializers
from .models import Employee
from departments.models import Department

class EmployeeSerializer(serializers.ModelSerializer):
    department_name = serializers.CharField(source='department.name', read_only=True)
    job_title = serializers.CharField(source='job.title', read_only=True, allow_null=True)
    profile_picture_url = serializers.SerializerMethodField()

    class Meta:
        model = Employee
        fields = [
            'id', 'name', 'father_name', 'cnic', 'profile_picture', 'profile_picture_url',
            'department', 'department_name', 'job', 'job_title',
            'designation', 'salary', 'joining_date', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']

    def get_profile_picture_url(self, obj):
        request = self.context.get('request')
        # Prefer employee's own picture
        if obj.profile_picture:
            return request.build_absolute_uri(obj.profile_picture.url) if request else obj.profile_picture.url
        # Fall back to linked user's profile picture (for portal-hired employees)
        if obj.user and obj.user.profile_picture:
            return request.build_absolute_uri(obj.user.profile_picture.url) if request else obj.user.profile_picture.url
        return None


class EmployeeDetailSerializer(serializers.ModelSerializer):
    department_name = serializers.CharField(source='department.name', read_only=True)
    job_title = serializers.CharField(source='job.title', read_only=True, allow_null=True)
    profile_picture_url = serializers.SerializerMethodField()

    class Meta:
        model = Employee
        fields = [
            'id', 'name', 'father_name', 'cnic', 'profile_picture', 'profile_picture_url',
            'department', 'department_name', 'job', 'job_title',
            'designation', 'salary', 'joining_date', 'created_at', 'updated_at'
        ]

    def get_profile_picture_url(self, obj):
        request = self.context.get('request')
        if obj.profile_picture:
            return request.build_absolute_uri(obj.profile_picture.url) if request else obj.profile_picture.url
        if obj.user and obj.user.profile_picture:
            return request.build_absolute_uri(obj.user.profile_picture.url) if request else obj.user.profile_picture.url
        return None


class EmployeeCreateUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Employee
        fields = ['name', 'father_name', 'cnic', 'profile_picture', 'job', 'designation', 'salary', 'joining_date']