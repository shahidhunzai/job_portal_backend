from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from .models import User, ActivityLog

class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        
        # Add custom claims
        token['user_type'] = user.user_type
        token['username'] = user.username
        token['email'] = user.email
        
        return token
    
    def validate(self, attrs):
        data = super().validate(attrs)
        
        # Add extra responses
        data['user_type'] = self.user.user_type
        data['username'] = self.user.username
        data['email'] = self.user.email
        data['user_id'] = self.user.id
        data['first_name'] = self.user.first_name
        data['last_name'] = self.user.last_name
        
        # Add profile picture URL if exists
        if self.user.profile_picture:
            request = self.context.get('request')
            if request:
                data['profile_picture'] = request.build_absolute_uri(self.user.profile_picture.url)
            else:
                data['profile_picture'] = self.user.profile_picture.url
        else:
            data['profile_picture'] = None
        
        return data

class AdminLoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)
    
    def validate(self, attrs):
        email = attrs.get('email')
        password = attrs.get('password')
        
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            raise serializers.ValidationError({'error': 'Invalid credentials'})
        
        # Check if user is super_admin or department
        if user.user_type not in ['super_admin', 'department']:
            raise serializers.ValidationError({'error': 'You do not have permission to access admin panel'})
        
        # Check password
        if not user.check_password(password):
            raise serializers.ValidationError({'error': 'Invalid credentials'})
        
        if not user.is_active:
            raise serializers.ValidationError({'error': 'User account is disabled'})
        
        attrs['user'] = user
        return attrs

class UserSerializer(serializers.ModelSerializer):
    profile_picture_url = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'user_type', 
                  'profile_picture', 'profile_picture_url', 'father_name', 'address', 
                  'cnic', 'current_job', 'experience', 'education', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_profile_picture_url(self, obj):
        if obj.profile_picture:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.profile_picture.url)
            return obj.profile_picture.url
        return None
    
class ActivityLogSerializer(serializers.ModelSerializer):
    user_username = serializers.CharField(source='user.username', read_only=True)
    user_type = serializers.CharField(source='user.user_type', read_only=True)
    
    class Meta:
        model = ActivityLog
        fields = ['id', 'user', 'user_username', 'user_type', 'action', 
                  'details', 'ip_address', 'timestamp']
        read_only_fields = ['id', 'timestamp']


class JobSeekerRegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)
    confirm_password = serializers.CharField(write_only=True)
    
    class Meta:
        model = User
        fields = [
            'username', 'email', 'password', 'confirm_password',
            'first_name', 'last_name', 'father_name', 'cnic',
            'address', 'current_job', 'experience', 'education',
            'profile_picture'
        ]
    
    def validate(self, attrs):
        if attrs['password'] != attrs['confirm_password']:
            raise serializers.ValidationError({'error': 'Passwords do not match'})
        
        # Check if email already exists
        if User.objects.filter(email=attrs['email']).exists():
            raise serializers.ValidationError({'error': 'Email already registered'})
        
        # Check if username already exists
        if User.objects.filter(username=attrs['username']).exists():
            raise serializers.ValidationError({'error': 'Username already taken'})
        
        return attrs
    
    def create(self, validated_data):
        validated_data.pop('confirm_password')
        password = validated_data.pop('password')
        
        user = User.objects.create(
            **validated_data,
            user_type='job_seeker'
        )
        user.set_password(password)
        user.save()
        
        return user


class JobSeekerLoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)
    
    def validate(self, attrs):
        email = attrs.get('email')
        password = attrs.get('password')
        
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            raise serializers.ValidationError({'error': 'Invalid credentials'})
        
        # Check if user is job seeker
        if user.user_type != 'job_seeker':
            raise serializers.ValidationError({'error': 'Invalid credentials'})
        
        # Check password
        if not user.check_password(password):
            raise serializers.ValidationError({'error': 'Invalid credentials'})
        
        if not user.is_active:
            raise serializers.ValidationError({'error': 'Account is disabled'})
        
        attrs['user'] = user
        return attrs


class JobSeekerProfileSerializer(serializers.ModelSerializer):
    profile_picture_url = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'first_name', 'last_name',
            'father_name', 'cnic', 'address', 'current_job',
            'experience', 'education', 'profile_picture', 'profile_picture_url',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'email', 'username', 'created_at', 'updated_at']
    
    def get_profile_picture_url(self, obj):
        if obj.profile_picture:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.profile_picture.url)
            return obj.profile_picture.url
        return None