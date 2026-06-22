from django.urls import path
from . import views

urlpatterns = [
    path('', views.application_list, name='application-list'),
    path('export/', views.export_applications, name='export-applications'),

    path('apply/<int:job_id>/', views.apply_for_job, name='apply-for-job'),
    path('my-applications/', views.my_applications, name='my-applications'),
    path('my-applications/<int:pk>/', views.my_application_detail, name='my-application-detail'),
    path('my-applications/<int:pk>/withdraw/', views.withdraw_application, name='withdraw-application'),

    path('<int:pk>/', views.application_detail, name='application-detail'),
    path('<int:pk>/assign-test/', views.assign_test, name='assign-test'),
    path('<int:pk>/schedule-interview/', views.schedule_interview, name='schedule-interview'),
    path('<int:pk>/update-status/', views.update_status, name='update-status'),
    path('<int:pk>/hire/', views.hire_applicant, name='hire-applicant'),
    path('<int:pk>/reject/', views.reject_applicant, name='reject-applicant'),
]