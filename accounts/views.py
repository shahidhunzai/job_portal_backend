from rest_framework import status, generics
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate
from django.db.models import Count, Q
from django.utils import timezone
from datetime import timedelta

from .models import User, ActivityLog, Resume
from .serializers import (
    AdminLoginSerializer,
    UserSerializer,
    ActivityLogSerializer,
    JobSeekerRegistrationSerializer,
    JobSeekerLoginSerializer,
    JobSeekerProfileSerializer,
)
from departments.models import Department
from jobs.models import Job
from applicants.models import Application
from employees.models import Employee
from tests.models import Chapter, Question


# Helper function to log activity
def log_activity(user, action, details=None, ip_address=None):
    ActivityLog.objects.create(
        user=user,
        action=action,
        details=details,
        ip_address=ip_address
    )


# Helper function to get client IP
def get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip

@api_view(['POST'])
@permission_classes([AllowAny])
def admin_login(request):
    """
    Admin login endpoint for Super Admin and Department users
    """
    serializer = AdminLoginSerializer(data=request.data)
    
    if serializer.is_valid():
        user = serializer.validated_data['user']
        
        # Generate tokens
        refresh = RefreshToken.for_user(user)
        access = refresh.access_token
        
        # Add custom claims
        access['user_type'] = user.user_type
        access['username'] = user.username
        
        # Log activity
        ip_address = get_client_ip(request)
        log_activity(user, 'Admin Login', f'{user.user_type} logged in', ip_address)
        
        response_data = {
            'access': str(access),
            'refresh': str(refresh),
            'user_type': user.user_type,
            'username': user.username,
            'email': user.email,
            'user_id': user.id,
            'first_name': user.first_name,
            'last_name': user.last_name,
        }
        
        # For department users, prioritize department logo
        if user.user_type == 'department' and hasattr(user, 'department'):
            response_data['department_id'] = user.department.id
            response_data['department_name'] = user.department.name
            
            # Get the logo from department (primary source)
            if user.department.logo:
                department_logo_url = request.build_absolute_uri(user.department.logo.url)
                response_data['profile_picture'] = department_logo_url  # Use department logo as profile picture
                response_data['department_logo'] = department_logo_url
                print(f"✓ Using department logo: {department_logo_url}")
            # Fallback to user profile picture
            elif user.profile_picture:
                user_pic_url = request.build_absolute_uri(user.profile_picture.url)
                response_data['profile_picture'] = user_pic_url
                response_data['department_logo'] = user_pic_url
                print(f"✓ Using user profile picture: {user_pic_url}")
            else:
                response_data['profile_picture'] = None
                response_data['department_logo'] = None
                print(f"✗ No logo found for department: {user.department.name}")
        else:
            # For super admin, just use profile picture
            if user.profile_picture:
                response_data['profile_picture'] = request.build_absolute_uri(user.profile_picture.url)
            else:
                response_data['profile_picture'] = None
            response_data['department_logo'] = None
        
        print(f"Final login response: {response_data}")
        
        return Response(response_data, status=status.HTTP_200_OK)
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def super_admin_dashboard(request):
    """
    Super Admin Dashboard - Returns statistics and insights
    """
    # Check if user is super admin
    if request.user.user_type != 'super_admin':
        return Response(
            {'error': 'You do not have permission to access this resource'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    # Get date ranges
    today = timezone.now().date()
    last_30_days = today - timedelta(days=30)
    last_7_days = today - timedelta(days=7)
    
    # Total counts
    total_departments = Department.objects.count()
    total_jobs = Job.objects.count()
    total_applications = Application.objects.count()
    total_employees = Employee.objects.count()
    total_job_seekers = User.objects.filter(user_type='job_seeker').count()
    
    # Active jobs
    active_jobs = Job.objects.filter(status='open').count()
    closed_jobs = Job.objects.filter(status='closed').count()
    
    # Recent statistics (last 30 days)
    recent_departments = Department.objects.filter(created_at__gte=last_30_days).count()
    recent_jobs = Job.objects.filter(created_at__gte=last_30_days).count()
    recent_applications = Application.objects.filter(applied_at__gte=last_30_days).count()
    recent_employees = Employee.objects.filter(created_at__gte=last_30_days).count()
    
    # Jobs by type
    jobs_by_type = Job.objects.values('job_type').annotate(count=Count('id'))
    
    # Jobs by selection type
    jobs_by_selection = Job.objects.values('selection_type').annotate(count=Count('id'))
    
    # Applications by status
    applications_by_status = Application.objects.values('status').annotate(count=Count('id'))
    
    # Top departments by jobs posted
    top_departments = Department.objects.annotate(
        job_count=Count('jobs')
    ).order_by('-job_count')[:5].values('id', 'name', 'job_count')
    
    # Top departments by employees
    top_departments_by_employees = Department.objects.annotate(
        employee_count=Count('employees')
    ).order_by('-employee_count')[:5].values('id', 'name', 'employee_count')
    
    # Recent activity (last 7 days)
    recent_activities = ActivityLog.objects.filter(
        timestamp__gte=last_7_days
    ).order_by('-timestamp')[:10]
    
    activity_serializer = ActivityLogSerializer(recent_activities, many=True)
    
    dashboard_data = {
        'total_counts': {
            'departments': total_departments,
            'jobs': total_jobs,
            'applications': total_applications,
            'employees': total_employees,
            'job_seekers': total_job_seekers,
            'active_jobs': active_jobs,
            'closed_jobs': closed_jobs,
        },
        'recent_stats': {
            'departments_last_30_days': recent_departments,
            'jobs_last_30_days': recent_jobs,
            'applications_last_30_days': recent_applications,
            'employees_last_30_days': recent_employees,
        },
        'jobs_distribution': {
            'by_type': list(jobs_by_type),
            'by_selection': list(jobs_by_selection),
        },
        'applications_by_status': list(applications_by_status),
        'top_departments_by_jobs': list(top_departments),
        'top_departments_by_employees': list(top_departments_by_employees),
        'recent_activities': activity_serializer.data,
    }
    
    return Response(dashboard_data, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def department_dashboard(request):
    """
    Department Dashboard - Returns statistics for the department
    """
    # Check if user is department
    if request.user.user_type != 'department':
        return Response(
            {'error': 'You do not have permission to access this resource'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    if not hasattr(request.user, 'department'):
        return Response(
            {'error': 'Department profile not found'},
            status=status.HTTP_404_NOT_FOUND
        )
    
    department = request.user.department
    
    # Get date ranges
    today = timezone.now().date()
    last_30_days = today - timedelta(days=30)
    last_7_days = today - timedelta(days=7)
    
    # Total counts
    total_jobs = Job.objects.filter(department=department).count()
    total_chapters = Chapter.objects.filter(department=department).count()
    total_employees = Employee.objects.filter(department=department).count()
    total_applications = Application.objects.filter(job__department=department).count()
    
    # Active jobs
    active_jobs = Job.objects.filter(department=department, status='open').count()
    closed_jobs = Job.objects.filter(department=department, status='closed').count()
    
    # Recent statistics (last 30 days)
    recent_jobs = Job.objects.filter(department=department, created_at__gte=last_30_days).count()
    recent_applications = Application.objects.filter(
        job__department=department, 
        applied_at__gte=last_30_days
    ).count()
    recent_employees = Employee.objects.filter(
        department=department, 
        created_at__gte=last_30_days
    ).count()
    
    # Jobs by type
    jobs_by_type = Job.objects.filter(department=department).values('job_type').annotate(count=Count('id'))
    
    # Jobs by selection type
    jobs_by_selection = Job.objects.filter(department=department).values('selection_type').annotate(count=Count('id'))
    
    # Applications by status
    applications_by_status = Application.objects.filter(
        job__department=department
    ).values('status').annotate(count=Count('id'))
    
    # Top jobs by applications
    top_jobs = Job.objects.filter(department=department).annotate(
        application_count=Count('applications')
    ).order_by('-application_count')[:5].values('id', 'title', 'application_count')
    
    # Recent activity (last 7 days)
    recent_activities = ActivityLog.objects.filter(
        user=request.user,
        timestamp__gte=last_7_days
    ).order_by('-timestamp')[:10]
    
    activity_serializer = ActivityLogSerializer(recent_activities, many=True)
    
    # Questions count
    total_questions = Question.objects.filter(chapter__department=department).count()
    
    dashboard_data = {
        'department_info': {
            'id': department.id,
            'name': department.name,
            'tagline': department.tagline,
            'ceo_name': department.ceo_name,
            'email': department.email,
        },
        'total_counts': {
            'jobs': total_jobs,
            'chapters': total_chapters,
            'questions': total_questions,
            'employees': total_employees,
            'applications': total_applications,
            'active_jobs': active_jobs,
            'closed_jobs': closed_jobs,
        },
        'recent_stats': {
            'jobs_last_30_days': recent_jobs,
            'applications_last_30_days': recent_applications,
            'employees_last_30_days': recent_employees,
        },
        'jobs_distribution': {
            'by_type': list(jobs_by_type),
            'by_selection': list(jobs_by_selection),
        },
        'applications_by_status': list(applications_by_status),
        'top_jobs_by_applications': list(top_jobs),
        'recent_activities': activity_serializer.data,
    }
    
    return Response(dashboard_data, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def admin_logout(request):
    """
    Admin logout endpoint
    """
    try:
        # Log activity
        ip_address = get_client_ip(request)
        log_activity(request.user, 'Admin Logout', f'{request.user.user_type} logged out', ip_address)
        
        return Response({'message': 'Logged out successfully'}, status=status.HTTP_200_OK)
    except Exception as e:
        return Response({'message': 'Logged out successfully'}, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def current_user(request):
    """
    Get current logged in user details with profile picture
    """
    serializer = UserSerializer(request.user, context={'request': request})
    return Response(serializer.data, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def activity_logs(request):
    """
    GET: List all activity logs (Super Admin sees all, Department sees only their logs)
    """
    
    # Super Admin sees all activity logs
    if request.user.user_type == 'super_admin':
        logs = ActivityLog.objects.all().select_related('user')
    # Department sees only their activity logs
    elif request.user.user_type == 'department':
        if not hasattr(request.user, 'department'):
            return Response(
                {'error': 'Department profile not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        logs = ActivityLog.objects.filter(user=request.user)
    else:
        return Response(
            {'error': 'You do not have permission to access this resource'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    # Search functionality
    search = request.query_params.get('search', None)
    if search:
        logs = logs.filter(
            Q(user__username__icontains=search) |
            Q(action__icontains=search) |
            Q(details__icontains=search)
        )
    
    # Filter by user type
    user_type_filter = request.query_params.get('user_type', None)
    if user_type_filter:
        logs = logs.filter(user__user_type=user_type_filter)
    
    # Filter by action
    action_filter = request.query_params.get('action', None)
    if action_filter:
        logs = logs.filter(action__icontains=action_filter)
    
    # Filter by date range
    start_date = request.query_params.get('start_date', None)
    end_date = request.query_params.get('end_date', None)
    
    if start_date:
        try:
            start_datetime = timezone.datetime.strptime(start_date, '%Y-%m-%d')
            logs = logs.filter(timestamp__gte=start_datetime)
        except ValueError:
            pass
    
    if end_date:
        try:
            end_datetime = timezone.datetime.strptime(end_date, '%Y-%m-%d')
            # Add one day to include the entire end date
            end_datetime = end_datetime + timedelta(days=1)
            logs = logs.filter(timestamp__lt=end_datetime)
        except ValueError:
            pass
    
    # Sorting
    sort_by = request.query_params.get('sort_by', '-timestamp')
    logs = logs.order_by(sort_by)
    
    # Pagination
    page_size = int(request.query_params.get('page_size', 50))
    page = int(request.query_params.get('page', 1))
    
    start_index = (page - 1) * page_size
    end_index = start_index + page_size
    
    total_count = logs.count()
    paginated_logs = logs[start_index:end_index]
    
    serializer = ActivityLogSerializer(paginated_logs, many=True)
    
    # Get unique actions for filter
    unique_actions = ActivityLog.objects.values_list('action', flat=True).distinct()
    
    return Response({
        'count': total_count,
        'page': page,
        'page_size': page_size,
        'total_pages': (total_count + page_size - 1) // page_size,
        'results': serializer.data,
        'unique_actions': list(unique_actions),
    }, status=status.HTTP_200_OK)


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def clear_activity_logs(request):
    """
    DELETE: Clear all activity logs (Super Admin only)
    """
    
    if request.user.user_type != 'super_admin':
        return Response(
            {'error': 'Only super admin can clear activity logs'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    # Get count before deletion
    count = ActivityLog.objects.count()
    
    # Delete all logs
    ActivityLog.objects.all().delete()
    
    # Log this action
    ip_address = get_client_ip(request)
    log_activity(
        request.user, 
        'Activity Logs Cleared', 
        f'Cleared {count} activity log entries',
        ip_address
    )
    
    return Response(
        {'message': f'Successfully cleared {count} activity log entries'}, 
        status=status.HTTP_200_OK
    )


@api_view(['POST'])
@permission_classes([AllowAny])
def job_seeker_register(request):
    """
    Job Seeker Registration
    """
    serializer = JobSeekerRegistrationSerializer(data=request.data)
    
    if serializer.is_valid():
        user = serializer.save()
        
        # Generate tokens
        refresh = RefreshToken.for_user(user)
        access = refresh.access_token
        
        # Add custom claims
        access['user_type'] = user.user_type
        access['username'] = user.username
        
        # Log activity
        ip_address = get_client_ip(request)
        log_activity(user, 'Job Seeker Registration', 'New job seeker registered', ip_address)
        
        response_data = {
            'access': str(access),
            'refresh': str(refresh),
            'user_type': user.user_type,
            'username': user.username,
            'email': user.email,
            'user_id': user.id,
            'first_name': user.first_name,
            'last_name': user.last_name,
        }
        
        if user.profile_picture:
            response_data['profile_picture'] = request.build_absolute_uri(user.profile_picture.url)
        else:
            response_data['profile_picture'] = None
        
        return Response(response_data, status=status.HTTP_201_CREATED)
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([AllowAny])
def job_seeker_login(request):
    """
    Job Seeker Login
    """
    serializer = JobSeekerLoginSerializer(data=request.data)
    
    if serializer.is_valid():
        user = serializer.validated_data['user']
        
        # Generate tokens
        refresh = RefreshToken.for_user(user)
        access = refresh.access_token
        
        # Add custom claims
        access['user_type'] = user.user_type
        access['username'] = user.username
        
        # Log activity
        ip_address = get_client_ip(request)
        log_activity(user, 'Job Seeker Login', 'Job seeker logged in', ip_address)
        
        response_data = {
            'access': str(access),
            'refresh': str(refresh),
            'user_type': user.user_type,
            'username': user.username,
            'email': user.email,
            'user_id': user.id,
            'first_name': user.first_name,
            'last_name': user.last_name,
        }
        
        if user.profile_picture:
            response_data['profile_picture'] = request.build_absolute_uri(user.profile_picture.url)
        else:
            response_data['profile_picture'] = None
        
        return Response(response_data, status=status.HTTP_200_OK)
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET', 'PUT', 'PATCH'])
@permission_classes([IsAuthenticated])
def job_seeker_profile(request):
    """
    GET: Get job seeker profile
    PUT/PATCH: Update job seeker profile
    """
    if request.user.user_type != 'job_seeker':
        return Response(
            {'error': 'Only job seekers can access this endpoint'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    if request.method == 'GET':
        serializer = JobSeekerProfileSerializer(request.user, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    elif request.method in ['PUT', 'PATCH']:
        partial = request.method == 'PATCH'
        serializer = JobSeekerProfileSerializer(
            request.user,
            data=request.data,
            partial=partial,
            context={'request': request}
        )
        
        if serializer.is_valid():
            serializer.save()
            
            # Log activity
            ip_address = get_client_ip(request)
            log_activity(request.user, 'Profile Updated', 'Job seeker updated profile', ip_address)
            
            return Response(serializer.data, status=status.HTTP_200_OK)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def job_seeker_change_password(request):
    """
    Change password for job seeker
    """
    if request.user.user_type != 'job_seeker':
        return Response(
            {'error': 'Only job seekers can access this endpoint'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    current_password = request.data.get('current_password')
    new_password = request.data.get('new_password')
    
    if not current_password or not new_password:
        return Response(
            {'error': 'Current password and new password are required'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Check current password
    if not request.user.check_password(current_password):
        return Response(
            {'error': 'Current password is incorrect'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Validate new password
    if len(new_password) < 8:
        return Response(
            {'error': 'New password must be at least 8 characters long'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Set new password
    request.user.set_password(new_password)
    request.user.save()
    
    # Log activity
    ip_address = get_client_ip(request)
    log_activity(request.user, 'Password Changed', 'Job seeker changed password', ip_address)
    
    return Response(
        {'message': 'Password changed successfully'},
        status=status.HTTP_200_OK
    )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def job_seeker_dashboard(request):
    """
    Job Seeker Dashboard Statistics
    """
    if request.user.user_type != 'job_seeker':
        return Response(
            {'error': 'Only job seekers can access this endpoint'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    from applicants.models import Application
    from jobs.models import Job
    
    # Get applications
    applications = Application.objects.filter(applicant=request.user)
    
    # Statistics
    total_applications = applications.count()
    pending = applications.filter(status='applied').count()
    test_completed = applications.filter(status='test_completed').count()
    test_passed = applications.filter(status='test_passed').count()
    test_failed = applications.filter(status='test_failed').count()
    interview_scheduled = applications.filter(status='interview_scheduled').count()
    accepted = applications.filter(status='hired').count()
    rejected = applications.filter(status='rejected').count()
    
    # Recent applications (last 5)
    recent_applications = applications.order_by('-applied_at')[:5]
    
    from applicants.serializers import ApplicationSerializer
    recent_apps_serializer = ApplicationSerializer(
        recent_applications,
        many=True,
        context={'request': request}
    )
    
    # Recommended jobs (latest 4 open jobs)
    recommended_jobs = Job.objects.filter(status='open').order_by('-created_at')[:4]
    
    from jobs.serializers import JobSerializer
    recommended_jobs_serializer = JobSerializer(
        recommended_jobs,
        many=True,
        context={'request': request}
    )
    
    dashboard_data = {
        'user_info': {
            'username': request.user.username,
            'email': request.user.email,
            'first_name': request.user.first_name,
            'last_name': request.user.last_name,
        },
        'statistics': {
            'total_applications': total_applications,
            'pending': pending,
            'test_completed': test_completed,
            'test_passed': test_passed,
            'test_failed': test_failed,
            'interview_scheduled': interview_scheduled,
            'accepted': accepted,
            'rejected': rejected,
        },
        'recent_applications': recent_apps_serializer.data,
        'recommended_jobs': recommended_jobs_serializer.data,
    }
    
    return Response(dashboard_data, status=status.HTTP_200_OK)

# ─── Resume CRUD ─────────────────────────────────────────────────────────────

@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def resume_list_create(request):
    """
    GET: List all resumes for the logged-in job seeker
    POST: Create a new resume
    """
    if request.user.user_type != 'job_seeker':
        return Response({'error': 'Only job seekers can manage resumes'}, status=status.HTTP_403_FORBIDDEN)

    if request.method == 'GET':
        resumes = Resume.objects.filter(user=request.user)
        data = []
        for r in resumes:
            data.append({
                'id': r.id,
                'title': r.title,
                'father_name': r.father_name,
                'address': r.address,
                'cnic': r.cnic,
                'current_job': r.current_job,
                'experience': r.experience,
                'education': r.education,
                'is_primary': r.is_primary,
                'created_at': r.created_at,
                'updated_at': r.updated_at,
            })
        return Response(data, status=status.HTTP_200_OK)

    elif request.method == 'POST':
        title = request.data.get('title', '').strip()
        father_name = request.data.get('father_name', '').strip()
        address = request.data.get('address', '').strip()
        cnic = request.data.get('cnic', '').strip()
        current_job = request.data.get('current_job', '').strip()
        experience = request.data.get('experience', '').strip()
        education = request.data.get('education', '').strip()
        is_primary = request.data.get('is_primary', False)

        if not all([title, father_name, address, cnic, experience, education]):
            return Response({'error': 'title, father_name, address, cnic, experience and education are required'}, status=status.HTTP_400_BAD_REQUEST)

        # If setting as primary, unset others
        if is_primary:
            Resume.objects.filter(user=request.user, is_primary=True).update(is_primary=False)

        # If this is the first resume, auto-make primary
        if Resume.objects.filter(user=request.user).count() == 0:
            is_primary = True

        resume = Resume.objects.create(
            user=request.user,
            title=title,
            father_name=father_name,
            address=address,
            cnic=cnic,
            current_job=current_job,
            experience=experience,
            education=education,
            is_primary=is_primary,
        )

        log_activity(request.user, 'Resume Created', f'Created resume: {title}', get_client_ip(request))

        return Response({
            'id': resume.id, 'title': resume.title, 'father_name': resume.father_name,
            'address': resume.address, 'cnic': resume.cnic, 'current_job': resume.current_job,
            'experience': resume.experience, 'education': resume.education,
            'is_primary': resume.is_primary, 'created_at': resume.created_at,
        }, status=status.HTTP_201_CREATED)


@api_view(['GET', 'PUT', 'DELETE'])
@permission_classes([IsAuthenticated])
def resume_detail(request, pk):
    """
    GET/PUT/DELETE a specific resume
    """
    if request.user.user_type != 'job_seeker':
        return Response({'error': 'Only job seekers can manage resumes'}, status=status.HTTP_403_FORBIDDEN)

    try:
        resume = Resume.objects.get(pk=pk, user=request.user)
    except Resume.DoesNotExist:
        return Response({'error': 'Resume not found'}, status=status.HTTP_404_NOT_FOUND)

    if request.method == 'GET':
        return Response({
            'id': resume.id, 'title': resume.title, 'father_name': resume.father_name,
            'address': resume.address, 'cnic': resume.cnic, 'current_job': resume.current_job,
            'experience': resume.experience, 'education': resume.education,
            'is_primary': resume.is_primary, 'created_at': resume.created_at,
        })

    elif request.method == 'PUT':
        resume.title = request.data.get('title', resume.title)
        resume.father_name = request.data.get('father_name', resume.father_name)
        resume.address = request.data.get('address', resume.address)
        resume.cnic = request.data.get('cnic', resume.cnic)
        resume.current_job = request.data.get('current_job', resume.current_job)
        resume.experience = request.data.get('experience', resume.experience)
        resume.education = request.data.get('education', resume.education)

        is_primary = request.data.get('is_primary', resume.is_primary)
        if is_primary and not resume.is_primary:
            Resume.objects.filter(user=request.user, is_primary=True).update(is_primary=False)
        resume.is_primary = is_primary
        resume.save()

        log_activity(request.user, 'Resume Updated', f'Updated resume: {resume.title}', get_client_ip(request))
        return Response({'message': 'Resume updated', 'id': resume.id, 'title': resume.title, 'is_primary': resume.is_primary})

    elif request.method == 'DELETE':
        if resume.is_primary and Resume.objects.filter(user=request.user).count() > 1:
            return Response({'error': 'Cannot delete primary resume. Set another as primary first.'}, status=status.HTTP_400_BAD_REQUEST)
        title = resume.title
        resume.delete()
        log_activity(request.user, 'Resume Deleted', f'Deleted resume: {title}', get_client_ip(request))
        return Response({'message': 'Resume deleted'}, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def set_primary_resume(request, pk):
    """Set a resume as the primary one"""
    if request.user.user_type != 'job_seeker':
        return Response({'error': 'Only job seekers can manage resumes'}, status=status.HTTP_403_FORBIDDEN)
    try:
        resume = Resume.objects.get(pk=pk, user=request.user)
    except Resume.DoesNotExist:
        return Response({'error': 'Resume not found'}, status=status.HTTP_404_NOT_FOUND)

    Resume.objects.filter(user=request.user, is_primary=True).update(is_primary=False)
    resume.is_primary = True
    resume.save()
    return Response({'message': f'"{resume.title}" is now your primary resume'})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def upload_profile_picture(request):
    """Upload/update profile picture for job seeker"""
    if request.user.user_type != 'job_seeker':
        return Response({'error': 'Only job seekers can upload profile pictures'}, status=status.HTTP_403_FORBIDDEN)

    if 'profile_picture' not in request.FILES:
        return Response({'error': 'No image provided'}, status=status.HTTP_400_BAD_REQUEST)

    file = request.FILES['profile_picture']
    allowed = ['image/jpeg', 'image/png', 'image/gif', 'image/webp']
    if file.content_type not in allowed:
        return Response({'error': 'Only JPEG, PNG, GIF and WebP images are allowed'}, status=status.HTTP_400_BAD_REQUEST)

    if file.size > 5 * 1024 * 1024:  # 5MB
        return Response({'error': 'Image must be under 5MB'}, status=status.HTTP_400_BAD_REQUEST)

    request.user.profile_picture = file
    request.user.save()

    pic_url = request.build_absolute_uri(request.user.profile_picture.url)
    log_activity(request.user, 'Profile Picture Updated', 'Uploaded new profile picture', get_client_ip(request))
    return Response({'message': 'Profile picture updated', 'profile_picture_url': pic_url})
