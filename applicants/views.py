from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.db.models import Q
from django.utils import timezone

from .models import Application, TestAssignment, TestResult, TestAnswer, Interview
from .serializers import (
    ApplicationSerializer, 
    ApplicationDetailSerializer,
    ApplicationCreateSerializer,
    TestAssignmentSerializer,
    InterviewSerializer
)
from jobs.models import Job
from employees.models import Employee
from accounts.views import log_activity, get_client_ip


# ==================== JOB SEEKER ENDPOINTS ====================

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def apply_for_job(request, job_id):
    """
    POST: Apply for a job (Job Seeker)
    Requires: profile_picture uploaded + at least one resume + resume_id in body
    """
    if request.user.user_type != 'job_seeker':
        return Response({'error': 'Only job seekers can apply for jobs'}, status=status.HTTP_403_FORBIDDEN)

    # Enforce profile picture
    if not request.user.profile_picture:
        return Response(
            {'error': 'Please upload a profile picture before applying.', 'code': 'no_profile_picture'},
            status=status.HTTP_400_BAD_REQUEST
        )

    # Enforce at least one resume
    from accounts.models import Resume
    if not Resume.objects.filter(user=request.user).exists():
        return Response(
            {'error': 'Please create at least one resume before applying.', 'code': 'no_resume'},
            status=status.HTTP_400_BAD_REQUEST
        )

    # Check job exists and is open
    try:
        job = Job.objects.get(pk=job_id, status='open')
    except Job.DoesNotExist:
        return Response({'error': 'Job not found or closed'}, status=status.HTTP_404_NOT_FOUND)

    # Check already applied
    if Application.objects.filter(job=job, applicant=request.user).exists():
        return Response({'error': 'You have already applied for this job'}, status=status.HTTP_400_BAD_REQUEST)

    serializer = ApplicationCreateSerializer(data=request.data)
    if serializer.is_valid():
        resume_id = serializer.validated_data.get('resume_id')
        try:
            resume = Resume.objects.get(pk=resume_id, user=request.user)
        except Resume.DoesNotExist:
            return Response({'error': 'Resume not found or does not belong to you'}, status=status.HTTP_404_NOT_FOUND)

        application = Application.objects.create(
            job=job,
            applicant=request.user,
            resume=resume,
            status='applied'
        )

        ip_address = get_client_ip(request)
        log_activity(request.user, 'Job Application', f'Applied for {job.title} at {job.department.name}', ip_address)

        result = ApplicationSerializer(application, context={'request': request})
        return Response(result.data, status=status.HTTP_201_CREATED)

    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def my_applications(request):
    """
    GET: Get all applications for logged-in job seeker
    """
    if request.user.user_type != 'job_seeker':
        return Response(
            {'error': 'Only job seekers can access this endpoint'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    applications = Application.objects.filter(applicant=request.user).select_related(
        'job', 'job__department'
    ).prefetch_related('test_assignment', 'interview')
    
    # Filter by status
    status_filter = request.query_params.get('status', None)
    if status_filter:
        applications = applications.filter(status=status_filter)
    
    # Search
    search = request.query_params.get('search', None)
    if search:
        applications = applications.filter(
            Q(job__title__icontains=search) |
            Q(job__department__name__icontains=search)
        )
    
    # Sorting
    sort_by = request.query_params.get('sort_by', '-applied_at')
    applications = applications.order_by(sort_by)
    
    serializer = ApplicationSerializer(applications, many=True, context={'request': request})
    return Response({'results': serializer.data}, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def my_application_detail(request, pk):
    """
    GET: Get application details for job seeker
    """
    try:
        application = Application.objects.select_related(
            'job', 'job__department'
        ).prefetch_related(
            'test_assignment', 'test_assignment__result', 'interview'
        ).get(pk=pk, applicant=request.user)
    except Application.DoesNotExist:
        return Response(
            {'error': 'Application not found'},
            status=status.HTTP_404_NOT_FOUND
        )
    
    serializer = ApplicationDetailSerializer(application, context={'request': request})
    return Response(serializer.data, status=status.HTTP_200_OK)


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def withdraw_application(request, pk):
    """
    DELETE: Withdraw application (only if status is 'applied')
    """
    try:
        application = Application.objects.get(pk=pk, applicant=request.user)
    except Application.DoesNotExist:
        return Response(
            {'error': 'Application not found'},
            status=status.HTTP_404_NOT_FOUND
        )
    
    # Can only withdraw if status is 'applied'
    if application.status != 'applied':
        return Response(
            {'error': 'Cannot withdraw application at this stage'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    job_title = application.job.title
    application.delete()
    
    # Log activity
    ip_address = get_client_ip(request)
    log_activity(
        request.user,
        'Application Withdrawn',
        f'Withdrew application for {job_title}',
        ip_address
    )
    
    return Response(
        {'message': 'Application withdrawn successfully'},
        status=status.HTTP_200_OK
    )


# ==================== DEPARTMENT ENDPOINTS ====================

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def application_list(request):
    """
    GET: List all applications (Department sees only their job applications)
    """
    # Only department can access
    if request.user.user_type != 'department':
        return Response(
            {'error': 'Only departments can access applications'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    if not hasattr(request.user, 'department'):
        return Response(
            {'error': 'Department profile not found'},
            status=status.HTTP_404_NOT_FOUND
        )
    
    # Get applications for department's jobs
    applications = Application.objects.filter(
        job__department=request.user.department
    ).select_related('job', 'applicant')
    
    # Search functionality
    search = request.query_params.get('search', None)
    if search:
        applications = applications.filter(
            Q(applicant__username__icontains=search) |
            Q(applicant__email__icontains=search) |
            Q(job__title__icontains=search)
        )
    
    # Filter by status
    status_filter = request.query_params.get('status', None)
    if status_filter:
        applications = applications.filter(status=status_filter)
    
    # Filter by job
    job_filter = request.query_params.get('job', None)
    if job_filter:
        applications = applications.filter(job_id=job_filter)
    
    # Sorting
    sort_by = request.query_params.get('sort_by', '-applied_at')
    applications = applications.order_by(sort_by)
    
    serializer = ApplicationSerializer(applications, many=True, context={'request': request})
    
    return Response({
        'count': applications.count(),
        'results': serializer.data
    }, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def application_detail(request, pk):
    """
    GET: Retrieve application details (Department)
    """
    try:
        application = Application.objects.select_related(
            'job', 'applicant', 'job__department'
        ).prefetch_related('test_assignment', 'interview').get(pk=pk)
    except Application.DoesNotExist:
        return Response(
            {'error': 'Application not found'}, 
            status=status.HTTP_404_NOT_FOUND
        )
    
    # Check permissions
    if request.user.user_type == 'department':
        if not hasattr(request.user, 'department') or application.job.department != request.user.department:
            return Response(
                {'error': 'You do not have permission to access this application'},
                status=status.HTTP_403_FORBIDDEN
            )
    else:
        return Response(
            {'error': 'You do not have permission to access this resource'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    serializer = ApplicationDetailSerializer(application, context={'request': request})
    return Response(serializer.data, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def assign_test(request, pk):
    """
    POST: Assign test to applicant (Department)
    """
    try:
        application = Application.objects.get(pk=pk)
    except Application.DoesNotExist:
        return Response({'error': 'Application not found'}, status=status.HTTP_404_NOT_FOUND)
    
    # Check permissions
    if request.user.user_type != 'department' or application.job.department != request.user.department:
        return Response({'error': 'Permission denied'}, status=status.HTTP_403_FORBIDDEN)
    
    # Validate status
    if application.status != 'applied':
        return Response(
            {'error': 'Can only assign test to newly applied candidates'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    serializer = TestAssignmentSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save(application=application)
        
        # Update application status
        application.status = 'test_assigned'
        application.save()
        
        # Log activity
        ip_address = get_client_ip(request)
        log_activity(
            request.user,
            'Test Assigned',
            f'Assigned test to {application.applicant.username} for {application.job.title}',
            ip_address
        )
        
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def schedule_interview(request, pk):
    """
    POST: Schedule interview for applicant (Department)
    """
    try:
        application = Application.objects.get(pk=pk)
    except Application.DoesNotExist:
        return Response({'error': 'Application not found'}, status=status.HTTP_404_NOT_FOUND)
    
    # Check permissions
    if request.user.user_type != 'department' or application.job.department != request.user.department:
        return Response({'error': 'Permission denied'}, status=status.HTTP_403_FORBIDDEN)
    
    # Validate status (can schedule after test_passed or directly from applied for interview-only jobs)
    valid_statuses = ['test_passed', 'applied']
    if application.status not in valid_statuses:
        return Response(
            {'error': f'Can only schedule interview for candidates with status: {", ".join(valid_statuses)}'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    serializer = InterviewSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save(application=application)
        
        # Update application status
        application.status = 'interview_scheduled'
        application.save()
        
        # Log activity
        ip_address = get_client_ip(request)
        log_activity(
            request.user,
            'Interview Scheduled',
            f'Scheduled interview for {application.applicant.username} for {application.job.title}',
            ip_address
        )
        
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['PATCH'])
@permission_classes([IsAuthenticated])
def update_status(request, pk):
    """
    PATCH: Update application status (Department)
    """
    try:
        application = Application.objects.get(pk=pk)
    except Application.DoesNotExist:
        return Response({'error': 'Application not found'}, status=status.HTTP_404_NOT_FOUND)
    
    # Check permissions
    if request.user.user_type != 'department' or application.job.department != request.user.department:
        return Response({'error': 'Permission denied'}, status=status.HTTP_403_FORBIDDEN)
    
    new_status = request.data.get('status')
    rejection_reason = request.data.get('rejection_reason', None)
    
    # Validate status
    valid_statuses = [
        'applied', 'test_assigned', 'test_completed', 'test_passed', 'test_failed',
        'interview_scheduled', 'interview_completed', 'waiting', 'notice_period', 'hired', 'rejected'
    ]
    
    if new_status not in valid_statuses:
        return Response({'error': 'Invalid status'}, status=status.HTTP_400_BAD_REQUEST)
    
    application.status = new_status
    if rejection_reason:
        application.rejection_reason = rejection_reason
    application.save()
    
    # Log activity
    ip_address = get_client_ip(request)
    log_activity(
        request.user,
        'Application Status Updated',
        f'Updated {application.applicant.username} status to {new_status} for {application.job.title}',
        ip_address
    )
    
    serializer = ApplicationSerializer(application, context={'request': request})
    return Response(serializer.data, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def hire_applicant(request, pk):
    """
    POST: Hire applicant (create employee record) (Department)
    """
    try:
        application = Application.objects.get(pk=pk)
    except Application.DoesNotExist:
        return Response({'error': 'Application not found'}, status=status.HTTP_404_NOT_FOUND)
    
    # Check permissions
    if request.user.user_type != 'department' or application.job.department != request.user.department:
        return Response({'error': 'Permission denied'}, status=status.HTTP_403_FORBIDDEN)
    
    # Validate status
    if application.status != 'notice_period':
        return Response(
            {'error': 'Can only hire candidates in notice_period status'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Check if already an employee
    if Employee.objects.filter(name=application.applicant.username, department=request.user.department).exists():
        return Response(
            {'error': 'This candidate is already an employee'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Get required data
    designation = request.data.get('designation', application.job.title)
    salary = request.data.get('salary')
    joining_date = request.data.get('joining_date', timezone.now().date())
    
    if not salary:
        return Response(
            {'error': 'Salary is required'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Create employee record
    employee = Employee.objects.create(
        department=request.user.department,
        user=application.applicant,
        name=application.applicant.get_full_name() or application.applicant.username,
        father_name=application.applicant.father_name or '',
        cnic=application.applicant.cnic or '',
        profile_picture=application.applicant.profile_picture if application.applicant.profile_picture else None,
        job=application.job,
        designation=designation,
        salary=salary,
        joining_date=joining_date
    )
    
    # Update application status
    application.status = 'hired'
    application.save()
    
    # Update job filled positions if field exists
    if hasattr(application.job, 'filled_positions'):
        application.job.filled_positions += 1
        application.job.save()
    
    # Log activity
    ip_address = get_client_ip(request)
    log_activity(
        request.user,
        'Applicant Hired',
        f'Hired {application.applicant.username} as {employee.designation}',
        ip_address
    )
    
    return Response({
        'message': 'Applicant hired successfully',
        'employee_id': employee.id
    }, status=status.HTTP_201_CREATED)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def reject_applicant(request, pk):
    """
    POST: Reject applicant (Department)
    """
    try:
        application = Application.objects.get(pk=pk)
    except Application.DoesNotExist:
        return Response({'error': 'Application not found'}, status=status.HTTP_404_NOT_FOUND)
    
    # Check permissions
    if request.user.user_type != 'department' or application.job.department != request.user.department:
        return Response({'error': 'Permission denied'}, status=status.HTTP_403_FORBIDDEN)
    
    # Get rejection reason
    rejection_reason = request.data.get('rejection_reason', 'No reason provided')
    
    # Update application status
    application.status = 'rejected'
    application.rejection_reason = rejection_reason
    application.save()
    
    # Log activity
    ip_address = get_client_ip(request)
    log_activity(
        request.user,
        'Applicant Rejected',
        f'Rejected {application.applicant.username} for {application.job.title}. Reason: {rejection_reason}',
        ip_address
    )
    
    return Response({
        'message': 'Applicant rejected successfully'
    }, status=status.HTTP_200_OK)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def export_applications(request):
    """
    GET: Export applications as CSV or PDF with current filters applied
    Query params: format=csv|pdf, search, status, job
    """
    import csv
    import io
    from django.http import HttpResponse

    if request.user.user_type != 'department':
        return Response({'error': 'Only departments can export applications'}, status=status.HTTP_403_FORBIDDEN)

    if not hasattr(request.user, 'department'):
        return Response({'error': 'Department profile not found'}, status=status.HTTP_404_NOT_FOUND)

    # Apply same filters as application_list
    applications = Application.objects.filter(
        job__department=request.user.department
    ).select_related('job', 'applicant', 'resume').prefetch_related(
        'test_assignment', 'test_assignment__result'
    )

    search = request.query_params.get('search', None)
    if search:
        applications = applications.filter(
            Q(applicant__username__icontains=search) |
            Q(applicant__email__icontains=search) |
            Q(job__title__icontains=search)
        )

    status_filter = request.query_params.get('status', None)
    if status_filter:
        applications = applications.filter(status=status_filter)

    job_filter = request.query_params.get('job', None)
    if job_filter:
        applications = applications.filter(job_id=job_filter)

    applications = applications.order_by('-applied_at')
    export_format = request.query_params.get('format', 'csv').lower()

    # ── CSV Export ────────────────────────────────────────────────────────────
    if export_format == 'csv':
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="applicants_export.csv"'

        writer = csv.writer(response)
        writer.writerow([
            'ID', 'Applicant Name', 'Email', 'Father Name', 'CNIC', 'Address',
            'Current Job', 'Job Title', 'Status', 'Applied On',
            'Resume Title', 'Education', 'Experience',
            'Test Score (%)', 'Test Passed', 'Test Completed At',
        ])

        for app in applications:
            u = app.applicant
            r = app.resume
            test_score = ''
            test_passed = ''
            test_completed_at = ''

            if hasattr(app, 'test_assignment') and hasattr(app.test_assignment, 'result'):
                res = app.test_assignment.result
                test_score = f"{res.percentage:.1f}"
                test_passed = 'Yes' if res.passed else 'No'
                test_completed_at = res.completed_at.strftime('%Y-%m-%d %H:%M')

            full_name = u.get_full_name() or u.username

            writer.writerow([
                app.id,
                full_name,
                u.email,
                u.father_name or (r.father_name if r else ''),
                u.cnic or (r.cnic if r else ''),
                u.address or (r.address if r else ''),
                u.current_job or (r.current_job if r else ''),
                app.job.title,
                app.status.replace('_', ' ').title(),
                app.applied_at.strftime('%Y-%m-%d'),
                r.title if r else '',
                r.education if r else (u.education or ''),
                r.experience if r else (u.experience or ''),
                test_score,
                test_passed,
                test_completed_at,
            ])

        return response

    # ── PDF Export ────────────────────────────────────────────────────────────
    elif export_format == 'pdf':
        try:
            from reportlab.lib.pagesizes import A4, landscape
            from reportlab.lib import colors
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
            from reportlab.lib.units import mm, cm
            from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, HRFlowable
            from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT
        except ImportError:
            return Response({'error': 'PDF generation requires reportlab. Install with: pip install reportlab'}, status=500)

        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=landscape(A4),
            rightMargin=15*mm, leftMargin=15*mm,
            topMargin=15*mm, bottomMargin=15*mm
        )

        styles = getSampleStyleSheet()
        dept = request.user.department

        # Custom styles
        title_style = ParagraphStyle('title', fontSize=18, fontName='Helvetica-Bold', textColor=colors.HexColor('#1e293b'), spaceAfter=4)
        sub_style   = ParagraphStyle('sub',   fontSize=10, fontName='Helvetica',     textColor=colors.HexColor('#64748b'), spaceAfter=2)
        cell_style  = ParagraphStyle('cell',  fontSize=8,  fontName='Helvetica',     textColor=colors.HexColor('#1e293b'), leading=11)
        head_style  = ParagraphStyle('head',  fontSize=8,  fontName='Helvetica-Bold',textColor=colors.white, leading=11)

        story = []

        # Header
        story.append(Paragraph(f"{dept.name} — Applicants Export", title_style))
        filters_desc = []
        if search:        filters_desc.append(f"Search: {search}")
        if status_filter: filters_desc.append(f"Status: {status_filter.replace('_',' ').title()}")
        if job_filter:    filters_desc.append(f"Job ID: {job_filter}")
        story.append(Paragraph(
            f"Generated: {__import__('datetime').datetime.now().strftime('%d %b %Y %H:%M')}  |  "
            f"Total: {applications.count()} applicant(s)"
            + (f"  |  Filters: {', '.join(filters_desc)}" if filters_desc else ""),
            sub_style
        ))
        story.append(Spacer(1, 6*mm))
        story.append(HRFlowable(width='100%', thickness=1, color=colors.HexColor('#e2e8f0')))
        story.append(Spacer(1, 4*mm))

        # Table header
        col_headers = [
            Paragraph('#', head_style),
            Paragraph('Applicant', head_style),
            Paragraph('Email', head_style),
            Paragraph('Father / CNIC', head_style),
            Paragraph('Job', head_style),
            Paragraph('Status', head_style),
            Paragraph('Applied', head_style),
            Paragraph('Education', head_style),
            Paragraph('Experience', head_style),
            Paragraph('Test Score', head_style),
        ]

        STATUS_COLORS = {
            'applied':             '#3b82f6',
            'test_assigned':       '#f59e0b',
            'test_completed':      '#06b6d4',
            'test_passed':         '#22c55e',
            'test_failed':         '#ef4444',
            'interview_scheduled': '#6366f1',
            'waiting':             '#eab308',
            'notice_period':       '#a78bfa',
            'hired':               '#14b8a6',
            'rejected':            '#f43f5e',
        }

        rows = [col_headers]
        row_colors = [colors.HexColor('#6366f1')]  # header row

        for i, app in enumerate(applications):
            u   = app.applicant
            r   = app.resume
            full_name = u.get_full_name() or u.username
            father = u.father_name or (r.father_name if r else '—')
            cnic   = u.cnic or (r.cnic if r else '—')
            edu    = (r.education if r else u.education or '—')[:120]
            exp    = (r.experience if r else u.experience or '—')[:120]

            test_score = '—'
            if hasattr(app, 'test_assignment') and hasattr(app.test_assignment, 'result'):
                res = app.test_assignment.result
                color_hex = '#22c55e' if res.passed else '#ef4444'
                test_score = Paragraph(
                    f'<font color="{color_hex}"><b>{res.percentage:.0f}%</b></font> {"✓" if res.passed else "✗"}',
                    cell_style
                )

            st_color = STATUS_COLORS.get(app.status, '#64748b')

            rows.append([
                Paragraph(str(app.id), cell_style),
                Paragraph(f'<b>{full_name}</b>', cell_style),
                Paragraph(u.email, cell_style),
                Paragraph(f'{father}<br/><font color="#64748b" size="7">{cnic}</font>', cell_style),
                Paragraph(app.job.title, cell_style),
                Paragraph(f'<font color="{st_color}"><b>{app.status.replace("_"," ").title()}</b></font>', cell_style),
                Paragraph(app.applied_at.strftime('%d %b %Y'), cell_style),
                Paragraph(edu, cell_style),
                Paragraph(exp, cell_style),
                test_score if isinstance(test_score, Paragraph) else Paragraph(test_score, cell_style),
            ])
            row_colors.append(colors.HexColor('#f8fafc') if i % 2 == 0 else colors.white)

        # Column widths (landscape A4 usable ~257mm)
        col_widths = [12*mm, 32*mm, 38*mm, 32*mm, 28*mm, 26*mm, 18*mm, 36*mm, 36*mm, 18*mm]

        table = Table(rows, colWidths=col_widths, repeatRows=1)

        ts = TableStyle([
            # Header
            ('BACKGROUND',  (0, 0), (-1, 0), colors.HexColor('#6366f1')),
            ('TEXTCOLOR',   (0, 0), (-1, 0), colors.white),
            ('FONTNAME',    (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE',    (0, 0), (-1, 0), 8),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.HexColor('#f8fafc'), colors.white]),
            # Grid
            ('GRID',        (0, 0), (-1, -1), 0.3, colors.HexColor('#e2e8f0')),
            ('LINEBELOW',   (0, 0), (-1, 0), 1,   colors.HexColor('#4f46e5')),
            # Padding
            ('TOPPADDING',  (0, 0), (-1, -1), 5),
            ('BOTTOMPADDING',(0, 0), (-1, -1), 5),
            ('LEFTPADDING', (0, 0), (-1, -1), 6),
            ('RIGHTPADDING',(0, 0), (-1, -1), 6),
            ('VALIGN',      (0, 0), (-1, -1), 'TOP'),
        ])
        table.setStyle(ts)
        story.append(table)

        # Footer
        story.append(Spacer(1, 8*mm))
        story.append(HRFlowable(width='100%', thickness=0.5, color=colors.HexColor('#e2e8f0')))
        story.append(Paragraph(
            f"Confidential — {dept.name} HR Department  |  {__import__('datetime').datetime.now().strftime('%d %b %Y')}",
            ParagraphStyle('footer', fontSize=7, textColor=colors.HexColor('#94a3b8'), alignment=TA_RIGHT)
        ))

        doc.build(story)
        buffer.seek(0)

        response = HttpResponse(buffer, content_type='application/pdf')
        response['Content-Disposition'] = 'attachment; filename="applicants_export.pdf"'
        return response

    return Response({'error': 'Invalid format. Use ?format=csv or ?format=pdf'}, status=400)