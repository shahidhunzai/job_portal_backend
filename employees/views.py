from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Q

from .models import Employee
from .serializers import (
    EmployeeSerializer, 
    EmployeeDetailSerializer, 
    EmployeeCreateSerializer,
    EmployeeUpdateSerializer
)
from accounts.views import log_activity, get_client_ip


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def employee_list_create(request):
    """
    GET: List all employees (Super Admin sees all, Department sees only their employees)
    POST: Create a new employee (Super Admin and Department)
    """
    
    if request.method == 'GET':
        # Super Admin sees all employees
        if request.user.user_type == 'super_admin':
            employees = Employee.objects.all()
        # Department sees only their employees
        elif request.user.user_type == 'department':
            if not hasattr(request.user, 'department'):
                return Response(
                    {'error': 'Department profile not found'},
                    status=status.HTTP_404_NOT_FOUND
                )
            employees = Employee.objects.filter(department=request.user.department)
        else:
            return Response(
                {'error': 'You do not have permission to access this resource'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Search functionality
        search = request.query_params.get('search', None)
        if search:
            employees = employees.filter(
                Q(user__username__icontains=search) |
                Q(user__email__icontains=search) |
                Q(designation__icontains=search) |
                Q(job__title__icontains=search)
            )
        
        # Filter by department (for super admin)
        department_filter = request.query_params.get('department', None)
        if department_filter and request.user.user_type == 'super_admin':
            employees = employees.filter(department_id=department_filter)
        
        # Sorting
        sort_by = request.query_params.get('sort_by', '-joining_date')
        employees = employees.order_by(sort_by)
        
        # Pagination
        page = int(request.query_params.get('page', 1))
        page_size = int(request.query_params.get('page_size', 50))
        start_index = (page - 1) * page_size
        end_index = start_index + page_size
        
        total_count = employees.count()
        paginated_employees = employees[start_index:end_index]
        
        serializer = EmployeeSerializer(
            paginated_employees, 
            many=True, 
            context={'request': request}
        )
        
        return Response({
            'count': total_count,
            'page': page,
            'page_size': page_size,
            'total_pages': (total_count + page_size - 1) // page_size,
            'results': serializer.data
        }, status=status.HTTP_200_OK)
    
    elif request.method == 'POST':
        # Only Super Admin and Department can create employees
        if request.user.user_type not in ['super_admin', 'department']:
            return Response(
                {'error': 'You do not have permission to create employees'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        serializer = EmployeeCreateSerializer(data=request.data)
        
        if serializer.is_valid():
            # If department user, automatically assign to their department
            if request.user.user_type == 'department':
                if not hasattr(request.user, 'department'):
                    return Response(
                        {'error': 'Department profile not found'},
                        status=status.HTTP_404_NOT_FOUND
                    )
                employee = serializer.save(department=request.user.department)
            else:
                # Super Admin must provide department
                if 'department' not in request.data:
                    return Response(
                        {'error': 'Department is required'},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                employee = serializer.save()
            
            # Log activity
            ip_address = get_client_ip(request)
            log_activity(
                request.user,
                'Employee Created',
                f'Created employee: {employee.user.username} as {employee.designation}',
                ip_address
            )
            
            # Return detailed employee data
            detail_serializer = EmployeeDetailSerializer(
                employee, 
                context={'request': request}
            )
            return Response(detail_serializer.data, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET', 'PUT', 'PATCH', 'DELETE'])
@permission_classes([IsAuthenticated])
def employee_detail(request, pk):
    """
    GET: Retrieve employee details
    PUT/PATCH: Update employee information
    DELETE: Delete employee
    """
    
    # Get the employee
    try:
        employee = Employee.objects.get(pk=pk)
    except Employee.DoesNotExist:
        return Response(
            {'error': 'Employee not found'}, 
            status=status.HTTP_404_NOT_FOUND
        )
    
    # Check permissions
    if request.user.user_type == 'super_admin':
        # Super admin can access all employees
        pass
    elif request.user.user_type == 'department':
        if not hasattr(request.user, 'department') or employee.department != request.user.department:
            return Response(
                {'error': 'You do not have permission to access this employee'},
                status=status.HTTP_403_FORBIDDEN
            )
    else:
        return Response(
            {'error': 'You do not have permission to access this resource'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    if request.method == 'GET':
        serializer = EmployeeDetailSerializer(employee, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    elif request.method in ['PUT', 'PATCH']:
        # Only Super Admin and Department can update employees
        if request.user.user_type not in ['super_admin', 'department']:
            return Response(
                {'error': 'You do not have permission to update employees'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        partial = request.method == 'PATCH'
        serializer = EmployeeUpdateSerializer(
            employee, 
            data=request.data, 
            partial=partial
        )
        
        if serializer.is_valid():
            serializer.save()
            
            # Log activity
            ip_address = get_client_ip(request)
            log_activity(
                request.user,
                'Employee Updated',
                f'Updated employee: {employee.user.username}',
                ip_address
            )
            
            # Return detailed employee data
            detail_serializer = EmployeeDetailSerializer(
                employee, 
                context={'request': request}
            )
            return Response(detail_serializer.data, status=status.HTTP_200_OK)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    elif request.method == 'DELETE':
        # Only Super Admin can delete employees
        if request.user.user_type != 'super_admin':
            return Response(
                {'error': 'Only super admin can delete employees'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        username = employee.user.username
        employee.delete()
        
        # Log activity
        ip_address = get_client_ip(request)
        log_activity(
            request.user,
            'Employee Deleted',
            f'Deleted employee: {username}',
            ip_address
        )
        
        return Response(
            {'message': 'Employee deleted successfully'},
            status=status.HTTP_200_OK
        )


@api_view(['PATCH'])
@permission_classes([IsAuthenticated])
def update_employee_status(request, pk):
    """
    PATCH: Update employee status (active/inactive)
    This is a NEW endpoint for Department portal
    """
    try:
        employee = Employee.objects.get(pk=pk)
    except Employee.DoesNotExist:
        return Response(
            {'error': 'Employee not found'}, 
            status=status.HTTP_404_NOT_FOUND
        )
    
    # Check permissions
    if request.user.user_type == 'super_admin':
        pass
    elif request.user.user_type == 'department':
        if not hasattr(request.user, 'department') or employee.department != request.user.department:
            return Response(
                {'error': 'Permission denied'}, 
                status=status.HTTP_403_FORBIDDEN
            )
    else:
        return Response(
            {'error': 'Permission denied'}, 
            status=status.HTTP_403_FORBIDDEN
        )
    
    # Check if Employee model has status field
    if not hasattr(employee, 'status'):
        return Response(
            {'error': 'Employee model does not have status field'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    new_status = request.data.get('status')
    
    if new_status not in ['active', 'inactive']:
        return Response(
            {'error': 'Invalid status. Must be active or inactive'}, 
            status=status.HTTP_400_BAD_REQUEST
        )
    
    employee.status = new_status
    employee.save()
    
    # Log activity
    ip_address = get_client_ip(request)
    log_activity(
        request.user,
        'Employee Status Updated',
        f'Updated {employee.user.username} status to {new_status}',
        ip_address
    )
    
    serializer = EmployeeSerializer(employee, context={'request': request})
    return Response(serializer.data, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def employee_statistics(request):
    """
    GET: Get employee statistics
    NEW endpoint for dashboard metrics
    """
    if request.user.user_type == 'super_admin':
        employees = Employee.objects.all()
    elif request.user.user_type == 'department':
        if not hasattr(request.user, 'department'):
            return Response(
                {'error': 'Department profile not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        employees = Employee.objects.filter(department=request.user.department)
    else:
        return Response(
            {'error': 'You do not have permission to access this resource'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    total_count = employees.count()
    
    statistics = {
        'total_employees': total_count,
    }
    
    # Add status counts if status field exists
    if total_count > 0 and hasattr(employees.first(), 'status'):
        statistics['active_employees'] = employees.filter(status='active').count()
        statistics['inactive_employees'] = employees.filter(status='inactive').count()
    
    return Response(statistics, status=status.HTTP_200_OK)


from rest_framework import status
from rest_framework.decorators import api_view, permission_classes, parser_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser
from django.db.models import Q

from .models import Employee
from .serializers import EmployeeSerializer, EmployeeDetailSerializer, EmployeeCreateUpdateSerializer
from accounts.views import log_activity, get_client_ip


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
@parser_classes([MultiPartParser, FormParser])
def employee_list_create(request):
    """
    GET: List all employees
    POST: Create a new employee
    """
    
    if request.method == 'GET':
        # Super Admin sees all employees
        if request.user.user_type == 'super_admin':
            employees = Employee.objects.all()
        # Department sees only their employees
        elif request.user.user_type == 'department':
            if not hasattr(request.user, 'department'):
                return Response(
                    {'error': 'Department profile not found'},
                    status=status.HTTP_404_NOT_FOUND
                )
            employees = Employee.objects.filter(department=request.user.department)
        else:
            return Response(
                {'error': 'You do not have permission to access this resource'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Search functionality
        search = request.query_params.get('search', None)
        if search:
            employees = employees.filter(
                Q(name__icontains=search) |
                Q(father_name__icontains=search) |
                Q(cnic__icontains=search) |
                Q(designation__icontains=search)
            )
        
        # Sorting
        sort_by = request.query_params.get('sort_by', '-joining_date')
        employees = employees.order_by(sort_by)
        
        serializer = EmployeeSerializer(employees, many=True, context={'request': request})
        
        return Response({
            'count': employees.count(),
            'results': serializer.data
        }, status=status.HTTP_200_OK)
    
    elif request.method == 'POST':
        # Only Super Admin and Department can create employees
        if request.user.user_type not in ['super_admin', 'department']:
            return Response(
                {'error': 'You do not have permission to create employees'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        serializer = EmployeeCreateUpdateSerializer(data=request.data)
        
        if serializer.is_valid():
            # If department user, automatically assign to their department
            if request.user.user_type == 'department':
                if not hasattr(request.user, 'department'):
                    return Response(
                        {'error': 'Department profile not found'},
                        status=status.HTTP_404_NOT_FOUND
                    )
                employee = serializer.save(department=request.user.department)
            else:
                # Super Admin must provide department
                if 'department' not in request.data:
                    return Response(
                        {'error': 'Department is required'},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                employee = serializer.save()
            
            # Log activity
            ip_address = get_client_ip(request)
            log_activity(
                request.user,
                'Employee Created',
                f'Created employee: {employee.name} as {employee.designation}',
                ip_address
            )
            
            # Return detailed employee data
            detail_serializer = EmployeeDetailSerializer(employee, context={'request': request})
            return Response(detail_serializer.data, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET', 'PUT', 'PATCH', 'DELETE'])
@permission_classes([IsAuthenticated])
@parser_classes([MultiPartParser, FormParser])
def employee_detail(request, pk):
    """
    GET: Retrieve employee details
    PUT/PATCH: Update employee information
    DELETE: Delete employee
    """
    
    # Get the employee
    try:
        employee = Employee.objects.get(pk=pk)
    except Employee.DoesNotExist:
        return Response(
            {'error': 'Employee not found'}, 
            status=status.HTTP_404_NOT_FOUND
        )
    
    # Check permissions
    if request.user.user_type == 'super_admin':
        pass
    elif request.user.user_type == 'department':
        if not hasattr(request.user, 'department') or employee.department != request.user.department:
            return Response(
                {'error': 'You do not have permission to access this employee'},
                status=status.HTTP_403_FORBIDDEN
            )
    else:
        return Response(
            {'error': 'You do not have permission to access this resource'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    if request.method == 'GET':
        serializer = EmployeeDetailSerializer(employee, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    elif request.method in ['PUT', 'PATCH']:
        # Only Super Admin and Department can update employees
        if request.user.user_type not in ['super_admin', 'department']:
            return Response(
                {'error': 'You do not have permission to update employees'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        partial = request.method == 'PATCH'
        serializer = EmployeeCreateUpdateSerializer(employee, data=request.data, partial=partial)
        
        if serializer.is_valid():
            serializer.save()
            
            # Log activity
            ip_address = get_client_ip(request)
            log_activity(
                request.user,
                'Employee Updated',
                f'Updated employee: {employee.name}',
                ip_address
            )
            
            # Return detailed employee data
            detail_serializer = EmployeeDetailSerializer(employee, context={'request': request})
            return Response(detail_serializer.data, status=status.HTTP_200_OK)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    elif request.method == 'DELETE':
        # Only Super Admin and Department can delete employees
        if request.user.user_type not in ['super_admin', 'department']:
            return Response(
                {'error': 'You do not have permission to delete employees'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        name = employee.name
        employee.delete()
        
        # Log activity
        ip_address = get_client_ip(request)
        log_activity(
            request.user,
            'Employee Deleted',
            f'Deleted employee: {name}',
            ip_address
        )
        
        return Response(
            {'message': 'Employee deleted successfully'},
            status=status.HTTP_200_OK
        )