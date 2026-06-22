from django.urls import path
from . import views

urlpatterns = [
    path('chapters/', views.chapter_list_create, name='chapter-list-create'),
    path('chapters/<int:pk>/', views.chapter_detail, name='chapter-detail'),
    path('questions/', views.question_list_create, name='question-list-create'),
    path('questions/<int:pk>/', views.question_detail, name='question-detail'),
       # Job Seeker test endpoints
    path('application/<int:application_id>/questions/', views.get_test_questions, name='get-test-questions'),
    path('application/<int:application_id>/submit/', views.submit_test, name='submit-test'),
    path('application/<int:application_id>/results/', views.get_test_results, name='get-test-results'),
]