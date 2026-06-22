from rest_framework import serializers
from .models import Application, TestAssignment, TestResult, TestAnswer, Interview
from jobs.models import Job
from accounts.models import User, Resume
from tests.models import Chapter, Question


class ApplicationSerializer(serializers.ModelSerializer):
    job_title = serializers.CharField(source='job.title', read_only=True)
    job_id = serializers.IntegerField(source='job.id', read_only=True)
    company_name = serializers.CharField(source='job.department.name', read_only=True)
    company_logo = serializers.SerializerMethodField()
    job_type = serializers.CharField(source='job.job_type', read_only=True)
    applicant_name = serializers.SerializerMethodField()
    applicant_email = serializers.CharField(source='applicant.email', read_only=True)
    applicant_profile_picture = serializers.SerializerMethodField()
    has_test = serializers.SerializerMethodField()
    test_score = serializers.SerializerMethodField()
    resume_details = serializers.SerializerMethodField()

    class Meta:
        model = Application
        fields = [
            'id', 'job_id', 'job_title', 'company_name', 'company_logo',
            'job_type', 'applicant_name', 'applicant_email', 'applicant_profile_picture',
            'status', 'has_test', 'test_score', 'resume_details', 'applied_at', 'updated_at'
        ]
        read_only_fields = ['id', 'applied_at', 'updated_at']

    def get_company_logo(self, obj):
        if obj.job.department.logo:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.job.department.logo.url)
            return obj.job.department.logo.url
        return None

    def get_applicant_name(self, obj):
        u = obj.applicant
        full = f"{u.first_name} {u.last_name}".strip()
        return full if full else u.username

    def get_applicant_profile_picture(self, obj):
        if obj.applicant.profile_picture:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.applicant.profile_picture.url)
        return None

    def get_has_test(self, obj):
        return hasattr(obj, 'test_assignment')

    def get_test_score(self, obj):
        if hasattr(obj, 'test_assignment') and hasattr(obj.test_assignment, 'result'):
            return obj.test_assignment.result.percentage
        return None

    def get_resume_details(self, obj):
        if obj.resume:
            r = obj.resume
            return {
                'id': r.id,
                'title': r.title,
                'father_name': r.father_name,
                'cnic': r.cnic,
                'address': r.address,
                'current_job': r.current_job,
                'experience': r.experience,
                'education': r.education,
            }
        return None


class TestAssignmentSerializer(serializers.ModelSerializer):
    chapter_name = serializers.CharField(source='chapter.name', read_only=True)

    class Meta:
        model = TestAssignment
        fields = ['id', 'chapter', 'chapter_name', 'deadline', 'pass_percentage', 'assigned_at']


class TestResultSerializer(serializers.ModelSerializer):
    class Meta:
        model = TestResult
        fields = ['id', 'score', 'total_questions', 'correct_answers', 'percentage', 'passed', 'completed_at']


class InterviewSerializer(serializers.ModelSerializer):
    class Meta:
        model = Interview
        fields = ['id', 'interview_link', 'interview_datetime', 'message', 'created_at']


class ApplicationDetailSerializer(serializers.ModelSerializer):
    job_details = serializers.SerializerMethodField()
    company_details = serializers.SerializerMethodField()
    test_details = serializers.SerializerMethodField()
    interview_details = serializers.SerializerMethodField()
    applicant_details = serializers.SerializerMethodField()
    resume_details = serializers.SerializerMethodField()

    class Meta:
        model = Application
        fields = [
            'id', 'job_details', 'company_details', 'applicant_details',
            'resume_details', 'test_details', 'interview_details',
            'status', 'rejection_reason', 'applied_at', 'updated_at'
        ]

    def get_job_details(self, obj):
        return {
            'id': obj.job.id,
            'title': obj.job.title,
            'description': obj.job.description,
            'job_type': obj.job.job_type,
            'selection_type': obj.job.selection_type,
            'salary_range': obj.job.salary_range,
            'vacancies': obj.job.vacancies,
            'filled_positions': obj.job.filled_positions,
        }

    def get_company_details(self, obj):
        request = self.context.get('request')
        logo_url = None
        if obj.job.department.logo and request:
            logo_url = request.build_absolute_uri(obj.job.department.logo.url)
        return {
            'id': obj.job.department.id,
            'name': obj.job.department.name,
            'tagline': obj.job.department.tagline,
            'ceo_name': obj.job.department.ceo_name,
            'email': obj.job.department.email,
            'logo_url': logo_url,
        }

    def get_test_details(self, obj):
        if hasattr(obj, 'test_assignment'):
            ta = obj.test_assignment
            result_data = None
            if hasattr(ta, 'result'):
                r = ta.result
                result_data = {
                    'score': r.score,
                    'total_questions': r.total_questions,
                    'correct_answers': r.correct_answers,
                    'percentage': r.percentage,
                    'passed': r.passed,
                    'completed_at': r.completed_at,
                }
            return {
                'has_test': True,
                'chapter_name': ta.chapter.name,
                'deadline': ta.deadline,
                'pass_percentage': ta.pass_percentage,
                'test_completed': hasattr(ta, 'result'),
                'result': result_data,
            }
        return {'has_test': False}

    def get_interview_details(self, obj):
        if hasattr(obj, 'interview'):
            iv = obj.interview
            return {
                'has_interview': True,
                'interview_link': iv.interview_link,
                'interview_datetime': iv.interview_datetime,
                'message': iv.message,
            }
        return {'has_interview': False}

    def get_applicant_details(self, obj):
        request = self.context.get('request')
        profile_pic = None
        if obj.applicant.profile_picture and request:
            profile_pic = request.build_absolute_uri(obj.applicant.profile_picture.url)
        u = obj.applicant
        return {
            'id': u.id,
            'username': u.username,
            'email': u.email,
            'first_name': u.first_name,
            'last_name': u.last_name,
            'full_name': f"{u.first_name} {u.last_name}".strip() or u.username,
            'father_name': u.father_name,
            'cnic': u.cnic,
            'address': u.address,
            'current_job': u.current_job,
            'experience': u.experience,
            'education': u.education,
            'profile_picture': profile_pic,
        }

    def get_resume_details(self, obj):
        if obj.resume:
            r = obj.resume
            return {
                'id': r.id,
                'title': r.title,
                'father_name': r.father_name,
                'cnic': r.cnic,
                'address': r.address,
                'current_job': r.current_job,
                'experience': r.experience,
                'education': r.education,
                'is_primary': r.is_primary,
            }
        # Fall back to user profile data if no resume attached
        u = obj.applicant
        return {
            'id': None,
            'title': 'Profile Data',
            'father_name': u.father_name or '',
            'cnic': u.cnic or '',
            'address': u.address or '',
            'current_job': u.current_job or '',
            'experience': u.experience or '',
            'education': u.education or '',
            'is_primary': False,
        }


class ApplicationCreateSerializer(serializers.Serializer):
    resume_id = serializers.IntegerField(required=True)

    def validate_resume_id(self, value):
        try:
            Resume.objects.get(pk=value)
        except Resume.DoesNotExist:
            raise serializers.ValidationError("Resume not found")
        return value
