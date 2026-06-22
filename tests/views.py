from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Q, Count
from applicants.models import Application, TestAssignment, TestResult, TestAnswer
from .models import Chapter, Question, MCQOption
from .serializers import (
    ChapterSerializer, 
    ChapterDetailSerializer, 
    ChapterCreateSerializer,
    QuestionSerializer,
    QuestionListSerializer,
    QuestionCreateSerializer
)
from accounts.views import log_activity, get_client_ip


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def chapter_list_create(request):
    """
    GET: List all chapters (Super Admin sees all, Department sees only their chapters)
    POST: Create a new chapter (Department only)
    """
    
    if request.method == 'GET':
        # Super Admin sees all chapters
        if request.user.user_type == 'super_admin':
            chapters = Chapter.objects.all().select_related('department')
        # Department sees only their chapters
        elif request.user.user_type == 'department':
            if not hasattr(request.user, 'department'):
                return Response(
                    {'error': 'Department profile not found'},
                    status=status.HTTP_404_NOT_FOUND
                )
            chapters = Chapter.objects.filter(department=request.user.department)
        else:
            return Response(
                {'error': 'You do not have permission to access this resource'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Search functionality
        search = request.query_params.get('search', None)
        if search:
            chapters = chapters.filter(
                Q(name__icontains=search) |
                Q(subtitle__icontains=search) |
                Q(description__icontains=search) |
                Q(department__name__icontains=search)
            )
        
        # Filter by department (for super admin)
        department_filter = request.query_params.get('department', None)
        if department_filter and request.user.user_type == 'super_admin':
            chapters = chapters.filter(department_id=department_filter)
        
        # Sorting
        sort_by = request.query_params.get('sort_by', '-created_at')
        chapters = chapters.order_by(sort_by)
        
        serializer = ChapterSerializer(
            chapters, 
            many=True, 
            context={'request': request}
        )
        
        return Response({
            'count': chapters.count(),
            'results': serializer.data
        }, status=status.HTTP_200_OK)
    
    elif request.method == 'POST':
        # Only department can create chapters
        if request.user.user_type != 'department':
            return Response(
                {'error': 'Only departments can create chapters'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        if not hasattr(request.user, 'department'):
            return Response(
                {'error': 'Department profile not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        serializer = ChapterCreateSerializer(data=request.data)
        
        if serializer.is_valid():
            chapter = serializer.save(department=request.user.department)
            
            # Log activity
            ip_address = get_client_ip(request)
            log_activity(
                request.user, 
                'Chapter Created', 
                f'Created chapter: {chapter.name}',
                ip_address
            )
            
            response_serializer = ChapterSerializer(
                chapter, 
                context={'request': request}
            )
            return Response(
                response_serializer.data, 
                status=status.HTTP_201_CREATED
            )
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET', 'PUT', 'DELETE'])
@permission_classes([IsAuthenticated])
def chapter_detail(request, pk):
    """
    GET: Retrieve chapter details with all questions
    PUT: Update chapter (Department only - their own chapters)
    DELETE: Delete chapter (Department only - their own chapters)
    """
    
    try:
        chapter = Chapter.objects.select_related('department').prefetch_related(
            'questions', 'questions__options'
        ).get(pk=pk)
    except Chapter.DoesNotExist:
        return Response(
            {'error': 'Chapter not found'}, 
            status=status.HTTP_404_NOT_FOUND
        )
    
    # Check permissions
    if request.user.user_type == 'department':
        if not hasattr(request.user, 'department') or chapter.department != request.user.department:
            return Response(
                {'error': 'You do not have permission to access this chapter'},
                status=status.HTTP_403_FORBIDDEN
            )
    elif request.user.user_type != 'super_admin':
        return Response(
            {'error': 'You do not have permission to access this resource'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    if request.method == 'GET':
        serializer = ChapterDetailSerializer(chapter, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    elif request.method == 'PUT':
        # Only department can update their own chapters
        if request.user.user_type != 'department':
            return Response(
                {'error': 'Only departments can update chapters'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        serializer = ChapterCreateSerializer(
            chapter, 
            data=request.data, 
            partial=True
        )
        
        if serializer.is_valid():
            serializer.save()
            
            # Log activity
            ip_address = get_client_ip(request)
            log_activity(
                request.user, 
                'Chapter Updated', 
                f'Updated chapter: {chapter.name}',
                ip_address
            )
            
            response_serializer = ChapterSerializer(chapter, context={'request': request})
            return Response(response_serializer.data, status=status.HTTP_200_OK)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    elif request.method == 'DELETE':
        # Only department can delete their own chapters
        if request.user.user_type != 'department':
            return Response(
                {'error': 'Only departments can delete chapters'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        chapter_name = chapter.name
        chapter.delete()
        
        # Log activity
        ip_address = get_client_ip(request)
        log_activity(
            request.user, 
            'Chapter Deleted', 
            f'Deleted chapter: {chapter_name}',
            ip_address
        )
        
        return Response(
            {'message': 'Chapter deleted successfully'}, 
            status=status.HTTP_204_NO_CONTENT
        )


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def question_list_create(request):
    """
    GET: List all questions
    POST: Create a new question (Department only)
    """
    
    if request.method == 'GET':
        # Super Admin sees all questions
        if request.user.user_type == 'super_admin':
            questions = Question.objects.all().select_related('chapter', 'chapter__department').prefetch_related('options')
        # Department sees only their questions
        elif request.user.user_type == 'department':
            if not hasattr(request.user, 'department'):
                return Response(
                    {'error': 'Department profile not found'},
                    status=status.HTTP_404_NOT_FOUND
                )
            questions = Question.objects.filter(
                chapter__department=request.user.department
            ).select_related('chapter').prefetch_related('options')
        else:
            return Response(
                {'error': 'You do not have permission to access this resource'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Filter by chapter
        chapter_filter = request.query_params.get('chapter', None)
        if chapter_filter:
            questions = questions.filter(chapter_id=chapter_filter)
        
        # Search functionality
        search = request.query_params.get('search', None)
        if search:
            questions = questions.filter(Q(question_text__icontains=search))
        
        # Sorting
        sort_by = request.query_params.get('sort_by', '-created_at')
        questions = questions.order_by(sort_by)
        
        serializer = QuestionListSerializer(questions, many=True)
        
        return Response({
            'count': questions.count(),
            'results': serializer.data
        }, status=status.HTTP_200_OK)
    
    elif request.method == 'POST':
        # Only department can create questions
        if request.user.user_type != 'department':
            return Response(
                {'error': 'Only departments can create questions'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        serializer = QuestionCreateSerializer(data=request.data)
        
        if serializer.is_valid():
            question = serializer.save()
            
            # Log activity
            ip_address = get_client_ip(request)
            log_activity(
                request.user, 
                'Question Created', 
                f'Created question in chapter: {question.chapter.name}',
                ip_address
            )
            
            response_serializer = QuestionSerializer(question)
            return Response(
                response_serializer.data, 
                status=status.HTTP_201_CREATED
            )
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET', 'PUT', 'DELETE'])
@permission_classes([IsAuthenticated])
def question_detail(request, pk):
    """
    GET: Retrieve question details
    PUT: Update question (Department only)
    DELETE: Delete question (Department only)
    """
    
    try:
        question = Question.objects.select_related('chapter', 'chapter__department').prefetch_related('options').get(pk=pk)
    except Question.DoesNotExist:
        return Response(
            {'error': 'Question not found'}, 
            status=status.HTTP_404_NOT_FOUND
        )
    
    # Check permissions
    if request.user.user_type == 'department':
        if not hasattr(request.user, 'department') or question.chapter.department != request.user.department:
            return Response(
                {'error': 'You do not have permission to access this question'},
                status=status.HTTP_403_FORBIDDEN
            )
    elif request.user.user_type != 'super_admin':
        return Response(
            {'error': 'You do not have permission to access this resource'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    if request.method == 'GET':
        serializer = QuestionSerializer(question)
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    elif request.method == 'PUT':
        # Only department can update their own questions
        if request.user.user_type != 'department':
            return Response(
                {'error': 'Only departments can update questions'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        serializer = QuestionCreateSerializer(
            question, 
            data=request.data, 
            partial=True
        )
        
        if serializer.is_valid():
            serializer.save()
            
            # Log activity
            ip_address = get_client_ip(request)
            log_activity(
                request.user, 
                'Question Updated', 
                f'Updated question in chapter: {question.chapter.name}',
                ip_address
            )
            
            response_serializer = QuestionSerializer(question)
            return Response(response_serializer.data, status=status.HTTP_200_OK)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    elif request.method == 'DELETE':
        # Only department can delete their own questions
        if request.user.user_type != 'department':
            return Response(
                {'error': 'Only departments can delete questions'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        chapter_name = question.chapter.name
        question.delete()
        
        # Log activity
        ip_address = get_client_ip(request)
        log_activity(
            request.user, 
            'Question Deleted', 
            f'Deleted question from chapter: {chapter_name}',
            ip_address
        )
        
        return Response(
            {'message': 'Question deleted successfully'}, 
            status=status.HTTP_204_NO_CONTENT
        )
    
# ==================== JOB SEEKER TEST ENDPOINTS ====================

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_test_questions(request, application_id):
    """
    GET: Get all test questions for an application (Job Seeker)
    """
    if request.user.user_type != 'job_seeker':
        return Response(
            {'error': 'Only job seekers can access this endpoint'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    # Get application
    try:
        application = Application.objects.select_related(
            'test_assignment', 'test_assignment__chapter'
        ).get(pk=application_id, applicant=request.user)
    except Application.DoesNotExist:
        return Response(
            {'error': 'Application not found'},
            status=status.HTTP_404_NOT_FOUND
        )
    
    # Check if test is assigned
    if not hasattr(application, 'test_assignment'):
        return Response(
            {'error': 'No test assigned for this application'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    test_assignment = application.test_assignment
    
    # Check if test already completed
    if hasattr(test_assignment, 'result'):
        return Response(
            {'error': 'Test already completed'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Check deadline
    from django.utils import timezone
    if test_assignment.deadline < timezone.now():
        return Response(
            {'error': 'Test deadline has passed'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Get questions from assigned chapter
    questions = Question.objects.filter(
        chapter=test_assignment.chapter
    ).prefetch_related('options')
    
    if not questions.exists():
        return Response(
            {'error': 'No questions found for this test'},
            status=status.HTTP_404_NOT_FOUND
        )
    
    from .serializers import QuestionForTestSerializer
    serializer = QuestionForTestSerializer(questions, many=True)
    
    test_info = {
        'application_id': application.id,
        'job_title': application.job.title,
        'company_name': application.job.department.name,
        'chapter_name': test_assignment.chapter.name,
        'total_questions': questions.count(),
        'pass_percentage': test_assignment.pass_percentage,
        'deadline': test_assignment.deadline,
        'questions': serializer.data,
    }
    
    return Response(test_info, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def submit_test(request, application_id):
    """
    POST: Submit test answers (Job Seeker)
    Expected data: { "answers": [{"question_id": 1, "selected_options": [1, 2]}, ...] }
    """
    if request.user.user_type != 'job_seeker':
        return Response(
            {'error': 'Only job seekers can access this endpoint'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    # Get application
    try:
        application = Application.objects.select_related(
            'test_assignment'
        ).get(pk=application_id, applicant=request.user)
    except Application.DoesNotExist:
        return Response(
            {'error': 'Application not found'},
            status=status.HTTP_404_NOT_FOUND
        )
    
    # Check if test assigned
    if not hasattr(application, 'test_assignment'):
        return Response(
            {'error': 'No test assigned'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    test_assignment = application.test_assignment
    
    # Check if already submitted
    if hasattr(test_assignment, 'result'):
        return Response(
            {'error': 'Test already submitted'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    answers = request.data.get('answers', [])
    
    if not answers:
        return Response(
            {'error': 'No answers provided'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Process answers
    total_questions = 0
    correct_answers = 0
    
    # Create test result
    test_result = TestResult.objects.create(
        test_assignment=test_assignment,
        score=0,
        total_questions=0,
        correct_answers=0,
        percentage=0,
        passed=False
    )
    
    for answer_data in answers:
        question_id = answer_data.get('question_id')
        selected_option_ids = answer_data.get('selected_options', [])
        
        try:
            question = Question.objects.prefetch_related('options').get(pk=question_id)
            total_questions += 1
            
            # Get correct options for this question
            correct_options = question.options.filter(is_correct=True).values_list('id', flat=True)
            correct_option_ids = set(correct_options)
            selected_option_ids_set = set(selected_option_ids)
            
            # Check if answer is correct
            is_correct = correct_option_ids == selected_option_ids_set
            
            if is_correct:
                correct_answers += 1
            
            # Save test answer
            test_answer = TestAnswer.objects.create(
                test_result=test_result,
                question=question,
                is_correct=is_correct
            )
            
            # Add selected options
            for option_id in selected_option_ids:
                try:
                    option = MCQOption.objects.get(pk=option_id)
                    test_answer.selected_options.add(option)
                except MCQOption.DoesNotExist:
                    continue
            
        except Question.DoesNotExist:
            continue
    
    # Calculate percentage
    if total_questions > 0:
        percentage = (correct_answers / total_questions) * 100
    else:
        percentage = 0
    
    # Update test result
    test_result.total_questions = total_questions
    test_result.correct_answers = correct_answers
    test_result.score = correct_answers  # Simple scoring: 1 point per correct answer
    test_result.percentage = round(percentage, 2)
    test_result.passed = percentage >= test_assignment.pass_percentage
    test_result.save()
    
    # Update application status
    if test_result.passed:
        application.status = 'test_passed'
    else:
        application.status = 'test_failed'
    application.save()
    
    # Log activity
    ip_address = get_client_ip(request)
    log_activity(
        request.user,
        'Test Submitted',
        f'Submitted test for {application.job.title} - Score: {percentage}%',
        ip_address
    )
    
    return Response({
        'message': 'Test submitted successfully',
        'score': test_result.score,
        'total_questions': total_questions,
        'correct_answers': correct_answers,
        'percentage': percentage,
        'passed': test_result.passed,
        'pass_percentage': test_assignment.pass_percentage,
    }, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_test_results(request, application_id):
    """
    GET: Get test results for an application (Job Seeker)
    """
    if request.user.user_type != 'job_seeker':
        return Response(
            {'error': 'Only job seekers can access this endpoint'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    # Get application
    try:
        application = Application.objects.select_related(
            'test_assignment', 'test_assignment__result'
        ).get(pk=application_id, applicant=request.user)
    except Application.DoesNotExist:
        return Response(
            {'error': 'Application not found'},
            status=status.HTTP_404_NOT_FOUND
        )
    
    # Check if test assigned
    if not hasattr(application, 'test_assignment'):
        return Response(
            {'error': 'No test assigned'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Check if test completed
    if not hasattr(application.test_assignment, 'result'):
        return Response(
            {'error': 'Test not yet completed'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    test_result = application.test_assignment.result
    
    # Get detailed answers
    test_answers = TestAnswer.objects.filter(
        test_result=test_result
    ).select_related('question').prefetch_related(
        'question__options', 'selected_options'
    )
    
    detailed_answers = []
    for answer in test_answers:
        question = answer.question
        correct_options = question.options.filter(is_correct=True)
        selected_options = answer.selected_options.all()
        
        detailed_answers.append({
            'question_id': question.id,
            'question_text': question.question_text,
            'options': [
                {
                    'id': opt.id,
                    'option_text': opt.option_text,
                    'is_correct': opt.is_correct,
                }
                for opt in question.options.all()
            ],
            'selected_options': [opt.id for opt in selected_options],
            'correct_options': [opt.id for opt in correct_options],
            'is_correct': answer.is_correct,
        })
    
    results = {
        'application_id': application.id,
        'job_title': application.job.title,
        'company_name': application.job.department.name,
        'chapter_name': application.test_assignment.chapter.name,
        'score': test_result.score,
        'total_questions': test_result.total_questions,
        'correct_answers': test_result.correct_answers,
        'percentage': test_result.percentage,
        'passed': test_result.passed,
        'pass_percentage': application.test_assignment.pass_percentage,
        'completed_at': test_result.completed_at,
        'detailed_answers': detailed_answers,
    }
    
    return Response(results, status=status.HTTP_200_OK)