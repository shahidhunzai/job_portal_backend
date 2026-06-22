from django.urls import path
from . import views

urlpatterns = [
    path('', views.job_list_create, name='job-list-create'),
    path('<int:pk>/', views.job_detail, name='job-detail'),
    path('<int:pk>/status/', views.job_status_update, name='job-status-update'),
    
    # Public endpoints (NEW - ADD THESE)
    path('public/', views.public_job_list, name='public-job-list'),
    path('public/<int:pk>/', views.public_job_detail, name='public-job-detail'),
    path('statistics/', views.job_statistics, name='job-statistics'),
]