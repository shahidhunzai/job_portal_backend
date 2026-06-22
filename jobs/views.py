from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.db.models import Q, Count

from .models import Job
from .serializers import JobSerializer, JobDetailSerializer, JobCreateSerializer
from accounts.views import log_activity, get_client_ip


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def job_list_create(request):
    """
    GET: List all jobs (Super Admin sees all, Department sees only their jobs)
    POST: Create a new job (Department only)
    """
    
    if request.method == 'GET':
        # Super Admin sees all jobs
        if request.user.user_type == 'super_admin':
            jobs = Job.objects.all().select_related('department')
        # Department sees only their jobs
        elif request.user.user_type == 'department':
            if not hasattr(request.user, 'department'):
                return Response(
                    {'error': 'Department profile not found'},
                    status=status.HTTP_404_NOT_FOUND
                )
            jobs = Job.objects.filter(department=request.user.department)
        else:
            return Response(
                {'error': 'You do not have permission to access this resource'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Search functionality
        search = request.query_params.get('search', None)
        if search:
            jobs = jobs.filter(
                Q(title__icontains=search) |
                Q(description__icontains=search) |
                Q(required_skills__icontains=search) |
                Q(department__name__icontains=search)
            )
        
        # Filter by status
        status_filter = request.query_params.get('status', None)
        if status_filter:
            jobs = jobs.filter(status=status_filter)
        
        # Filter by job type
        job_type_filter = request.query_params.get('job_type', None)
        if job_type_filter:
            jobs = jobs.filter(job_type=job_type_filter)
        
        # Filter by selection type
        selection_type_filter = request.query_params.get('selection_type', None)
        if selection_type_filter:
            jobs = jobs.filter(selection_type=selection_type_filter)
        
        # Sorting
        sort_by = request.query_params.get('sort_by', '-created_at')
        jobs = jobs.order_by(sort_by)
        
        serializer = JobSerializer(
            jobs, 
            many=True, 
            context={'request': request}
        )
        
        return Response({
            'count': jobs.count(),
            'results': serializer.data
        }, status=status.HTTP_200_OK)
    
    elif request.method == 'POST':
        # Only department can create jobs
        if request.user.user_type != 'department':
            return Response(
                {'error': 'Only departments can create jobs'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        if not hasattr(request.user, 'department'):
            return Response(
                {'error': 'Department profile not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        serializer = JobCreateSerializer(data=request.data)
        
        if serializer.is_valid():
            job = serializer.save(department=request.user.department)
            
            # Log activity
            ip_address = get_client_ip(request)
            log_activity(
                request.user, 
                'Job Created', 
                f'Created job: {job.title}',
                ip_address
            )
            
            response_serializer = JobSerializer(
                job, 
                context={'request': request}
            )
            return Response(
                response_serializer.data, 
                status=status.HTTP_201_CREATED
            )
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET', 'PUT', 'DELETE', 'PATCH'])
@permission_classes([IsAuthenticated])
def job_detail(request, pk):
    """
    GET: Retrieve job details
    PUT/PATCH: Update job (Department only - their own jobs)
    DELETE: Delete job (Department only - their own jobs)
    """
    
    try:
        job = Job.objects.select_related('department').get(pk=pk)
    except Job.DoesNotExist:
        return Response(
            {'error': 'Job not found'}, 
            status=status.HTTP_404_NOT_FOUND
        )
    
    # Check permissions
    if request.user.user_type == 'department':
        if not hasattr(request.user, 'department') or job.department != request.user.department:
            return Response(
                {'error': 'You do not have permission to access this job'},
                status=status.HTTP_403_FORBIDDEN
            )
    elif request.user.user_type != 'super_admin':
        return Response(
            {'error': 'You do not have permission to access this resource'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    if request.method == 'GET':
        serializer = JobDetailSerializer(job, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    elif request.method in ['PUT', 'PATCH']:
        # Only department can update their own jobs
        if request.user.user_type != 'department':
            return Response(
                {'error': 'Only departments can update jobs'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        serializer = JobCreateSerializer(
            job, 
            data=request.data, 
            partial=(request.method == 'PATCH')
        )
        
        if serializer.is_valid():
            serializer.save()
            
            # Log activity
            ip_address = get_client_ip(request)
            log_activity(
                request.user, 
                'Job Updated', 
                f'Updated job: {job.title}',
                ip_address
            )
            
            response_serializer = JobSerializer(job, context={'request': request})
            return Response(response_serializer.data, status=status.HTTP_200_OK)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    elif request.method == 'DELETE':
        # Only department can delete their own jobs
        if request.user.user_type != 'department':
            return Response(
                {'error': 'Only departments can delete jobs'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        job_title = job.title
        job.delete()
        
        # Log activity
        ip_address = get_client_ip(request)
        log_activity(
            request.user, 
            'Job Deleted', 
            f'Deleted job: {job_title}',
            ip_address
        )
        
        return Response(
            {'message': 'Job deleted successfully'}, 
            status=status.HTTP_204_NO_CONTENT
        )


@api_view(['PATCH'])
@permission_classes([IsAuthenticated])
def job_status_update(request, pk):
    """
    Update job status (open/closed) - Department only
    """
    try:
        job = Job.objects.get(pk=pk)
    except Job.DoesNotExist:
        return Response(
            {'error': 'Job not found'}, 
            status=status.HTTP_404_NOT_FOUND
        )
    
    # Only department can update their own job status
    if request.user.user_type != 'department':
        return Response(
            {'error': 'Only departments can update job status'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    if not hasattr(request.user, 'department') or job.department != request.user.department:
        return Response(
            {'error': 'You do not have permission to update this job'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    new_status = request.data.get('status')
    if new_status not in ['open', 'closed']:
        return Response(
            {'error': 'Invalid status. Must be "open" or "closed"'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    job.status = new_status
    job.save()
    
    # Log activity
    ip_address = get_client_ip(request)
    log_activity(
        request.user, 
        'Job Status Updated', 
        f'Changed job "{job.title}" status to {new_status}',
        ip_address
    )
    
    serializer = JobSerializer(job, context={'request': request})
    return Response(serializer.data, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([AllowAny])  # Public endpoint
def public_job_list(request):
    """
    GET: List all open jobs (Public - no authentication required)
    """
    # Only show open jobs to public
    jobs = Job.objects.filter(status='open')
    
    # Search functionality
    search = request.query_params.get('search', None)
    if search:
        jobs = jobs.filter(
            Q(title__icontains=search) |
            Q(description__icontains=search) |
            Q(department__name__icontains=search)
        )
    
    # Filter by department
    department = request.query_params.get('department', None)
    if department:
        jobs = jobs.filter(department_id=department)
    
    # Filter by job type
    job_type = request.query_params.get('job_type', None)
    if job_type:
        jobs = jobs.filter(job_type=job_type)
    
    # Filter by selection type
    selection_type = request.query_params.get('selection_type', None)
    if selection_type:
        jobs = jobs.filter(selection_type=selection_type)
    
    # Filter by salary range
    min_salary = request.query_params.get('min_salary', None)
    max_salary = request.query_params.get('max_salary', None)
    if min_salary:
        jobs = jobs.filter(salary_max__gte=min_salary)
    if max_salary:
        jobs = jobs.filter(salary_min__lte=max_salary)
    
    # Sorting
    sort_by = request.query_params.get('sort_by', '-created_at')
    jobs = jobs.order_by(sort_by)
    
    # Pagination
    page = int(request.query_params.get('page', 1))
    page_size = int(request.query_params.get('page_size', 20))
    start_index = (page - 1) * page_size
    end_index = start_index + page_size
    
    total_count = jobs.count()
    paginated_jobs = jobs[start_index:end_index]
    
    serializer = JobSerializer(paginated_jobs, many=True, context={'request': request})
    
    return Response({
        'count': total_count,
        'page': page,
        'page_size': page_size,
        'total_pages': (total_count + page_size - 1) // page_size,
        'results': serializer.data
    }, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([AllowAny])  # Public endpoint
def public_job_detail(request, pk):
    """
    GET: Get job details (Public - no authentication required)
    """
    try:
        job = Job.objects.get(pk=pk, status='open')
    except Job.DoesNotExist:
        return Response(
            {'error': 'Job not found or closed'},
            status=status.HTTP_404_NOT_FOUND
        )
    
    serializer = JobDetailSerializer(job, context={'request': request})
    return Response(serializer.data, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([AllowAny])
def job_statistics(request):
    """
    GET: Public statistics for homepage
    """
    from departments.models import Department
    from applicants.models import Application
    
    total_jobs = Job.objects.filter(status='open').count()
    total_companies = Department.objects.count()
    total_applications = Application.objects.count()
    
    # Job types distribution
    job_types = Job.objects.filter(status='open').values('job_type').annotate(count=Count('id'))
    
    return Response({
        'total_jobs': total_jobs,
        'total_companies': total_companies,
        'total_applications': total_applications,
        'job_types': list(job_types),
    }, status=status.HTTP_200_OK)