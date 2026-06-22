from rest_framework import status, generics
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Q, Count

from .models import Department
from .serializers import (
    DepartmentSerializer, 
    DepartmentCreateSerializer, 
    DepartmentDetailSerializer
)
from accounts.views import log_activity, get_client_ip


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def department_list_create(request):
    """
    GET: List all departments with search and filter
    POST: Create a new department (Super Admin only)
    """
    
    if request.method == 'GET':
        # Only super admin can view all departments
        if request.user.user_type != 'super_admin':
            return Response(
                {'error': 'You do not have permission to access this resource'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        departments = Department.objects.all()
        
        # Search functionality
        search = request.query_params.get('search', None)
        if search:
            departments = departments.filter(
                Q(name__icontains=search) |
                Q(ceo_name__icontains=search) |
                Q(email__icontains=search) |
                Q(tagline__icontains=search)
            )
        
        # Sorting
        sort_by = request.query_params.get('sort_by', '-created_at')
        departments = departments.order_by(sort_by)
        
        serializer = DepartmentSerializer(
            departments, 
            many=True, 
            context={'request': request}
        )
        
        return Response({
            'count': departments.count(),
            'results': serializer.data
        }, status=status.HTTP_200_OK)
    
    elif request.method == 'POST':
        # Only super admin can create departments
        if request.user.user_type != 'super_admin':
            return Response(
                {'error': 'You do not have permission to create departments'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        serializer = DepartmentCreateSerializer(data=request.data)
        
        if serializer.is_valid():
            department = serializer.save()
            
            # Log activity
            ip_address = get_client_ip(request)
            log_activity(
                request.user, 
                'Department Created', 
                f'Created department: {department.name}',
                ip_address
            )
            
            response_serializer = DepartmentSerializer(
                department, 
                context={'request': request}
            )
            return Response(
                response_serializer.data, 
                status=status.HTTP_201_CREATED
            )
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET', 'PUT', 'DELETE'])
@permission_classes([IsAuthenticated])
def department_detail(request, pk):
    """
    GET: Retrieve department details
    PUT: Update department (Super Admin only)
    DELETE: Delete department (Super Admin only)
    """
    
    try:
        department = Department.objects.get(pk=pk)
    except Department.DoesNotExist:
        return Response(
            {'error': 'Department not found'}, 
            status=status.HTTP_404_NOT_FOUND
        )
    
    if request.method == 'GET':
        # Super admin can view any department
        if request.user.user_type != 'super_admin':
            return Response(
                {'error': 'You do not have permission to access this resource'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        serializer = DepartmentDetailSerializer(
            department, 
            context={'request': request}
        )
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    elif request.method == 'PUT':
        # Only super admin can update
        if request.user.user_type != 'super_admin':
            return Response(
                {'error': 'You do not have permission to update departments'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        serializer = DepartmentSerializer(
            department, 
            data=request.data, 
            partial=True,
            context={'request': request}
        )
        
        if serializer.is_valid():
            serializer.save()
            
            # Log activity
            ip_address = get_client_ip(request)
            log_activity(
                request.user, 
                'Department Updated', 
                f'Updated department: {department.name}',
                ip_address
            )
            
            return Response(serializer.data, status=status.HTTP_200_OK)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    elif request.method == 'DELETE':
        # Only super admin can delete
        if request.user.user_type != 'super_admin':
            return Response(
                {'error': 'You do not have permission to delete departments'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        department_name = department.name
        
        # Delete associated user
        if department.user:
            department.user.delete()
        
        department.delete()
        
        # Log activity
        ip_address = get_client_ip(request)
        log_activity(
            request.user, 
            'Department Deleted', 
            f'Deleted department: {department_name}',
            ip_address
        )
        
        return Response(
            {'message': 'Department deleted successfully'}, 
            status=status.HTTP_204_NO_CONTENT
        )