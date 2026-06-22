from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from . import views

urlpatterns = [
    # Admin endpoints
    path('admin/login/', views.admin_login, name='admin-login'),
    path('admin/logout/', views.admin_logout, name='admin-logout'),
    path('admin/dashboard/', views.super_admin_dashboard, name='super-admin-dashboard'),
    path('department/dashboard/', views.department_dashboard, name='department-dashboard'),
    path('current-user/', views.current_user, name='current-user'),
    path('activity-logs/', views.activity_logs, name='activity-logs'),
    path('activity-logs/clear/', views.clear_activity_logs, name='clear-activity-logs'),

    # Job Seeker endpoints
    path('job-seeker/register/', views.job_seeker_register, name='job-seeker-register'),
    path('job-seeker/login/', views.job_seeker_login, name='job-seeker-login'),
    path('job-seeker/profile/', views.job_seeker_profile, name='job-seeker-profile'),
    path('job-seeker/upload-profile-picture/', views.upload_profile_picture, name='upload-profile-picture'),
    path('job-seeker/change-password/', views.job_seeker_change_password, name='job-seeker-change-password'),
    path('job-seeker/dashboard/', views.job_seeker_dashboard, name='job-seeker-dashboard'),

    # Resume endpoints
    path('job-seeker/resumes/', views.resume_list_create, name='resume-list-create'),
    path('job-seeker/resumes/<int:pk>/', views.resume_detail, name='resume-detail'),
    path('job-seeker/resumes/<int:pk>/set-primary/', views.set_primary_resume, name='set-primary-resume'),

    # Token refresh
    path('token/refresh/', TokenRefreshView.as_view(), name='token-refresh'),
]
