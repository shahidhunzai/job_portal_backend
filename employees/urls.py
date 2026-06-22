from django.urls import path
from . import views

urlpatterns = [
    # Existing endpoints
    path('', views.employee_list_create, name='employee-list-create'),
    path('<int:pk>/', views.employee_detail, name='employee-detail'),
    
    # New endpoints for Department portal
    path('<int:pk>/update-status/', views.update_employee_status, name='update-employee-status'),
    path('statistics/', views.employee_statistics, name='employee-statistics'),
]