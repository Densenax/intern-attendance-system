from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.db.models import Q
from django.views.decorators.csrf import csrf_protect, csrf_exempt
from django.http import JsonResponse, HttpResponseForbidden
from django.http import HttpResponse
from django.utils import timezone
from .models import Student, Employee, Attendance, User, Visitor, Event, TempVisitor, QRCode
import json
import uuid
import qrcode
from io import BytesIO
from django.core.files.base import ContentFile
from django.middleware.csrf import get_token
from django.urls import reverse
from itertools import chain
from .models import Attendance
from django.core.files import File
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth import update_session_auth_hash
from django.template import loader
from django.db.models.functions import TruncDate
from django.db.models import Count
from datetime import datetime, timedelta
from django.template.loader import get_template
from xhtml2pdf import pisa
from dateutil import parser
from django.shortcuts import get_object_or_404
from django.core.serializers.json import DjangoJSONEncoder

def is_authorized_staff(user):
    return user.is_superuser or user.is_staff or (hasattr(user, 'role') and user.role == 'security')

def is_admin(user):
    return user.is_superuser or user.role == 'admin'

def home(request):
    if not request.user.is_authenticated:
        return redirect('demons:login')
    if request.user.is_superuser or request.user.role == 'admin':
        return redirect('demons:admin_dashboard')
    elif request.user.role == 'security':
        return redirect('demons:security_dashboard')
    return redirect('demons:login')

@csrf_protect
def user_login(request):
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            if user.is_superuser or user.role == 'admin':
                return redirect('demons:admin_dashboard')
            elif user.role == 'security':
                return redirect('demons:security_dashboard')
            else:
                return redirect('demons:home')
        else:
            messages.error(request, 'Invalid username or password.')
    return render(request, 'login.html')

@login_required
def user_logout(request):
    logout(request)
    return redirect('demons:login')

def is_admin(user):
    return user.is_authenticated and user.role == User.ADMIN

def is_security(user):
    return user.is_authenticated and user.role == User.SECURITY

@login_required
@user_passes_test(is_admin)
def admin_dashboard(request):
    # Get visitor counts
    visitor_check_ins = Visitor.objects.filter(time_in__isnull=False).count()
    visitor_check_outs = Visitor.objects.filter(time_out__isnull=False).count()
    
    # Fetch all events
    all_events = Event.objects.all()
    initial_events = json.dumps(list(all_events.values('id', 'title', 'start')), cls=DjangoJSONEncoder)

    context = {
        'total_check_ins': Attendance.get_total_check_ins() + visitor_check_ins,
        'total_check_outs': Attendance.get_total_check_outs() + visitor_check_outs,
        'student_check_ins': Attendance.get_student_check_ins(),
        'student_check_outs': Attendance.get_student_check_outs(),
        'employee_check_ins': Attendance.get_employee_check_ins(),
        'employee_check_outs': Attendance.get_employee_check_outs(),
        'visitor_check_ins': visitor_check_ins,
        'visitor_check_outs': visitor_check_outs,
        'initial_events': initial_events,
    }
    return render(request, 'admin_dashboard.html', context)

@login_required
def add_user(request):
    if not is_admin(request.user):
        messages.error(request, 'You do not have permission to access this page.')
        return redirect('demons:home')
        
    if request.method == 'POST':
        try:
            name = request.POST.get('name')
            user_type = request.POST.get('user_type')
            id_number = request.POST.get('id_number')
            department_or_course = request.POST.get('department_or_course')

            if not all([name, user_type, id_number, department_or_course]):
                messages.error(request, 'All fields are required.')
                return redirect('demons:users')

            if user_type == 'student':
                if Student.objects.filter(student_id=id_number).exists():
                    messages.error(request, 'A student with this ID already exists.')
                    return redirect('demons:users')
                    
                user = Student(
                    name=name,
                    student_id=id_number,
                    course=department_or_course
                )
                success_message = "Student registered successfully"
            else:
                if Employee.objects.filter(employee_id=id_number).exists():
                    messages.error(request, 'An employee with this ID already exists.')
                    return redirect('demons:users')
                    
                user = Employee(
                    name=name,
                    employee_id=id_number,
                    department=department_or_course
                )
                success_message = "Employee registered successfully"

            user.save()

            # Generate QR code
            qr = qrcode.QRCode(version=1, box_size=10, border=5)
            qr.add_data(str(user.id))
            qr.make(fit=True)
            img = qr.make_image(fill_color="black", back_color="white")
            buffer = BytesIO()
            img.save(buffer, format='PNG')
            buffer.seek(0)

            user.qr_code.save(f'{user_type}_{id_number}.png', File(buffer), save=True)
            
            messages.success(request, success_message)
            return redirect('demons:users')
            
        except Exception as e:
            messages.error(request, f'An error occurred while registering the user: {str(e)}')
            return redirect('demons:users')

    return redirect('demons:users')

@login_required
@user_passes_test(is_authorized_staff)
def security_dashboard(request):
    # Get visitor counts
    visitor_check_ins = Visitor.objects.filter(time_in__isnull=False).count()
    visitor_check_outs = Visitor.objects.filter(time_out__isnull=False).count()
    
    context = {
        'total_check_ins': Attendance.get_total_check_ins() + visitor_check_ins,
        'total_check_outs': Attendance.get_total_check_outs() + visitor_check_outs,
        'student_check_ins': Attendance.get_student_check_ins(),
        'student_check_outs': Attendance.get_student_check_outs(),
        'employee_check_ins': Attendance.get_employee_check_ins(),
        'employee_check_outs': Attendance.get_employee_check_outs(),
        'visitor_check_ins': visitor_check_ins,
        'visitor_check_outs': visitor_check_outs,
    }
    return render(request, 'security_dashboard.html', context)

@login_required
@user_passes_test(lambda u: u.role == 'security')
def get_recent_activity(request):
    recent_activity = request.session.get('recent_activity', [])
    return JsonResponse({'recent_activity': recent_activity})

@login_required
@user_passes_test(is_admin)
def users(request):
    if not is_admin(request.user):
        messages.error(request, 'You do not have permission to access this page.')
        return redirect('demons:home')
        
    students = Student.objects.all()
    employees = Employee.objects.all()
    context = {
        'students': students,
        'employees': employees,
    }
    return render(request, 'users.html', context)

@login_required
@user_passes_test(is_admin)
@csrf_protect
def register_student(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        contact_info = request.POST.get('contact_info')
        student_id = request.POST.get('student_id')
        department = request.POST.get('department')

        if not all([name, contact_info, student_id, department]):
            messages.error(request, "Please fill in all required fields.")
            return render(request, 'register_student.html')

        student = Student(
            name=name,
            contact_info=contact_info,
            student_id=student_id,
            department=department
        )

        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(str(student.id))
        qr.make(fit=True)
        qr_image = qr.make_image(fill_color="black", back_color="white")
        
        buffer = BytesIO()
        qr_image.save(buffer, format="PNG")
        buffer.seek(0)
        student.qr_code.save(f"qr_{student.id}.png", ContentFile(buffer.getvalue()), save=False)
        student.save()

        messages.success(request, "Student registered successfully.")
        return render(request, 'register_student.html', {'success': True})

    return render(request, 'register_student.html')

@login_required
@user_passes_test(is_admin)
@csrf_protect
def register_employee(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        contact_info = request.POST.get('contact_info')
        employee_id = request.POST.get('employee_id')
        department = request.POST.get('department')

        if not all([name, contact_info, employee_id, department]):
            messages.error(request, "Please fill in all required fields.")
            return render(request, 'register_employee.html')

        employee = Employee(
            name=name,
            contact_info=contact_info,
            employee_id=employee_id,
            department=department
        )

        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(str(employee.id))
        qr.make(fit=True)
        qr_image = qr.make_image(fill_color="black", back_color="white")
        
        buffer = BytesIO()
        qr_image.save(buffer, format="PNG")
        buffer.seek(0)
        employee.qr_code.save(f"qr_{employee.id}.png", ContentFile(buffer.getvalue()), save=False)
        employee.save()

        messages.success(request, "Employee registered successfully.")
        return render(request, 'register_employee.html', {'success': True})

    return render(request, 'register_employee.html')

@login_required
@user_passes_test(is_security)
def register_visitor(request):
    if request.method == 'POST':
        qr_code_id = request.POST.get('qr_code')
        if not qr_code_id:
            messages.error(request, 'No QR code provided')
            return redirect('demons:visitors')

        try:
            qr_code = QRCode.objects.get(code_id=qr_code_id)
            if qr_code.is_registered:
                messages.error(request, 'QR code is already in use')
                return redirect('demons:visitors')

            # Create temporary visitor record
            temp_visitor = TempVisitor.objects.create(
                qr_code=qr_code,
                name=f"{request.POST['first_name']} {request.POST['last_name']}",
                contact_info=request.POST['contact_info'],
                purpose=request.POST['purpose']
            )
            
            # Update QR code status
            qr_code.is_active = False
            qr_code.is_registered = True
            qr_code.save()
            
            messages.success(request, 'Visitor registered successfully!')
            return redirect('demons:visitors')

        except QRCode.DoesNotExist:
            messages.error(request, 'Invalid QR code')
            return redirect('demons:visitors')

    return redirect('demons:visitors')

@login_required
@user_passes_test(is_security)
def scan(request):
    return render(request, 'scan.html', {'user': request.user})

@login_required
@user_passes_test(lambda u: u.role == 'security' or u.role == 'admin')
@login_required
@user_passes_test(is_authorized_staff)
def visitors(request):
    visitors = Visitor.objects.all().order_by('-id')
    return render(request, 'visitors.html', {'visitors': visitors})

@csrf_exempt
def process_qr(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            qr_data = data.get('qr_data')
            
            if not qr_data:
                return JsonResponse({
                    'success': False,
                    'message': "No QR code data provided"
                })

            # First check if it's a visitor QR code (4 digits)
            if len(qr_data) == 4 and qr_data.isdigit():
                try:
                    qr_code = QRCode.objects.get(code_id=qr_data)
                    return handle_visitor_attendance(qr_code)
                except QRCode.DoesNotExist:
                    return JsonResponse({
                        'success': False,
                        'message': "Invalid visitor QR code"
                    })

            # If not a visitor QR code, try to find a student or employee
            try:
                student = Student.objects.get(id=qr_data)
                return handle_attendance(student, 'Student')
            except (Student.DoesNotExist, ValueError):
                try:
                    employee = Employee.objects.get(id=qr_data)
                    return handle_attendance(employee, 'Employee')
                except (Employee.DoesNotExist, ValueError):
                    return JsonResponse({
                        'success': False,
                        'message': "Invalid QR code"
                    })

        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': f"An error occurred: {str(e)}"
            })
    
    return JsonResponse({
        'success': False,
        'message': "Invalid request method"
    })

def handle_attendance(user, user_type):
    current_time = timezone.localtime(timezone.now())
    last_attendance = Attendance.objects.filter(
        **{user_type.lower(): user}
    ).order_by('-check_in_timestamp').first()

    if last_attendance and not last_attendance.check_out_timestamp:
        # User is checking out
        last_attendance.check_out_timestamp = current_time
        last_attendance.save()
        action = 'Checked Out'
    else:
        # User is checking in
        Attendance.objects.create(**{
            user_type.lower(): user,
            'check_in_timestamp': current_time
        })
        action = 'Checked In'

    return JsonResponse({
        'success': True,
        'name': user.name,
        'user_type': user_type,
        'user_id': user.student_id if user_type == 'Student' else user.employee_id,
        'additional_info': user.course if user_type == 'Student' else user.department,
        'info_type': 'Course' if user_type == 'Student' else 'Department',
        'action': action,
        'timestamp': current_time.strftime("%I:%M:%S %p"),
        'profile_photo': user.profile_photo.url if user.profile_photo else None,
    })

def handle_visitor_attendance(qr_code):
    temp_visitor = TempVisitor.objects.filter(qr_code=qr_code).first()
    
    if temp_visitor:
        current_time = timezone.localtime(timezone.now())
        if temp_visitor.time_in:
            # Visitor is checking out
            visitor = temp_visitor.move_to_permanent()
            visitor.time_out = current_time
            visitor.save()
            return JsonResponse({
                'success': True,
                'name': visitor.name,
                'user_type': 'Visitor',
                'user_id': qr_code.code_id,
                'additional_info': visitor.purpose,
                'info_type': 'Purpose',
                'action': 'Checked Out',
                'timestamp': current_time.strftime("%I:%M:%S %p"),
            })
        else:
            # Visitor is checking in
            temp_visitor.time_in = current_time
            temp_visitor.save()
            return JsonResponse({
                'success': True,
                'name': temp_visitor.name,
                'user_type': 'Visitor',
                'user_id': qr_code.code_id,
                'additional_info': temp_visitor.purpose,
                'info_type': 'Purpose',
                'action': 'Checked In',
                'timestamp': current_time.strftime("%I:%M:%S %p"),
            })
    else:
        # QR code is not registered - return registration needed response
        return JsonResponse({
            'success': True,
            'needs_registration': True,
            'qr_code': qr_code.code_id,
            'message': "Please register visitor information"
        })

@login_required
@user_passes_test(is_authorized_staff)
def settings(request):
    if request.method == 'POST':
        user = request.user
        user.username = request.POST.get('username')
        user.email = request.POST.get('email')
        user.first_name = request.POST.get('first_name')
        user.last_name = request.POST.get('last_name')

        if request.POST.get('password'):
            if request.POST.get('password') == request.POST.get('password_confirm'):
                user.set_password(request.POST.get('password'))
                update_session_auth_hash(request, user)  # Keep the user logged in
            else:
                messages.error(request, 'Passwords do not match.')
                return render(request, 'settings.html')

        user.save()
        messages.success(request, 'Your information has been updated successfully.')
        return redirect('demons:settings')

    return render(request, 'settings.html')

@login_required
@user_passes_test(is_admin)
def attendance_report(request):
    # Get parameters from the request
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    search_query = request.GET.get('search', '')

    # Set default date range to last 7 days if not provided
    if not start_date:
        start_date = (timezone.now() - timedelta(days=7)).date()
    else:
        start_date = datetime.strptime(start_date, '%Y-%m-%d').date()

    if not end_date:
        end_date = timezone.now().date()
    else:
        end_date = datetime.strptime(end_date, '%Y-%m-%d').date()

    # Create datetime range for exact date filtering
    start_datetime = timezone.make_aware(datetime.combine(start_date, datetime.min.time()))
    end_datetime = timezone.make_aware(datetime.combine(end_date, datetime.max.time()))

    # Get visitor counts for the date range
    #visitor_count = Visitor.objects.filter(
    #    Q(time_in__range=(start_datetime, end_datetime)) |
    #    Q(time_out__range=(start_datetime, end_datetime))
    #).count()

    # Get student and employee counts from Attendance model
    student_count = Attendance.objects.filter(
        check_in_timestamp__range=(start_datetime, end_datetime),
        student__isnull=False
    ).values('student').distinct().count()
    
    employee_count = Attendance.objects.filter(
        check_in_timestamp__range=(start_datetime, end_datetime),
        employee__isnull=False
    ).values('employee').distinct().count()
    
    visitor_count = Visitor.objects.filter(
        Q(time_in__range=(start_datetime, end_datetime)) |
        Q(time_out__range=(start_datetime, end_datetime))
    ).count()

    # Process attendance data for template
    student_attendance = []
    employee_attendance = []
    visitor_attendance = []

    # Apply search filter if provided
    if search_query:
        # Check for student matches
        student_matches = Student.objects.filter(
            Q(name__icontains=search_query) | Q(student_id__icontains=search_query)
        ).exists()
        
        # Check for employee matches
        employee_matches = Employee.objects.filter(
            Q(name__icontains=search_query) | Q(employee_id__icontains=search_query)
        ).exists()
        
        # Check for visitor matches
        visitor_matches = Visitor.objects.filter(
            Q(name__icontains=search_query) | Q(contact_info__icontains=search_query)
        ).exists()

        if student_matches:
            student_records = Attendance.objects.filter(
                check_in_timestamp__range=(start_datetime, end_datetime),
                student__isnull=False
            ).filter(
                Q(student__name__icontains=search_query) | 
                Q(student__student_id__icontains=search_query)
            ).select_related('student')
            
            for record in student_records:
                student_attendance.append({
                    'name': record.student.name,
                    'id_number': record.student.student_id,
                    'course': record.student.course,
                    'date': record.check_in_timestamp.date(),
                    'time_in': record.check_in_timestamp,
                    'time_out': record.check_out_timestamp
                })
        
        elif employee_matches:
            employee_records = Attendance.objects.filter(
                check_in_timestamp__range=(start_datetime, end_datetime),
                employee__isnull=False
            ).filter(
                Q(employee__name__icontains=search_query) | 
                Q(employee__employee_id__icontains=search_query)
            ).select_related('employee')
            
            for record in employee_records:
                employee_attendance.append({
                    'name': record.employee.name,
                    'id_number': record.employee.employee_id,
                    'department': record.employee.department,
                    'date': record.check_in_timestamp.date(),
                    'time_in': record.check_in_timestamp,
                    'time_out': record.check_out_timestamp
                })
        
        elif visitor_matches:
            visitor_attendance = Visitor.objects.filter(
                Q(time_in__range=(start_datetime, end_datetime)) |
                Q(time_out__range=(start_datetime, end_datetime))
            ).order_by('time_in')

            if search_query:
                visitor_attendance = visitor_attendance.filter(
                    Q(name__icontains=search_query) | 
                    Q(contact_info__icontains=search_query)
                )

            visitor_attendance = list(visitor_attendance.values(
                'name', 'contact_info', 'purpose', 'time_in', 'time_out'
            ))
    else:
        # If no search query, get all records
        student_records = Attendance.objects.filter(
            check_in_timestamp__range=(start_datetime, end_datetime),
            student__isnull=False
        ).select_related('student')

        for record in student_records:
            student_attendance.append({
                'name': record.student.name,
                'id_number': record.student.student_id,
                'course': record.student.course,
                'date': record.check_in_timestamp.date(),
                'time_in': record.check_in_timestamp,
                'time_out': record.check_out_timestamp
            })

        employee_records = Attendance.objects.filter(
            check_in_timestamp__range=(start_datetime, end_datetime),
            employee__isnull=False
        ).select_related('employee')

        for record in employee_records:
            employee_attendance.append({
                'name': record.employee.name,
                'id_number': record.employee.employee_id,
                'department': record.employee.department,
                'date': record.check_in_timestamp.date(),
                'time_in': record.check_in_timestamp,
                'time_out': record.check_out_timestamp
            })

        visitor_attendance = Visitor.objects.filter(
            Q(time_in__range=(start_datetime, end_datetime)) |
            Q(time_out__range=(start_datetime, end_datetime))
        ).order_by('time_in')

        visitor_attendance = list(visitor_attendance.values(
            'name', 'contact_info', 'purpose', 'time_in', 'time_out'
        ))

    # Sort all attendance lists by date and time
    student_attendance.sort(key=lambda x: (x['date'], x['time_in']))
    employee_attendance.sort(key=lambda x: (x['date'], x['time_in']))
    visitor_attendance.sort(key=lambda x: (x['time_in'] if x['time_in'] else x['time_out']))

    context = {
        'start_date': start_date,
        'end_date': end_date,
        'search_query': search_query,
        'student_attendance': student_attendance,
        'employee_attendance': employee_attendance,
        'visitor_attendance': visitor_attendance,
        'student_count': student_count,
        'employee_count': employee_count,
        'visitor_count': visitor_count,
    }

    return render(request, 'attendance_report.html', context)

@login_required
@user_passes_test(is_admin)
def generate_employee_pdf_report(request):
    # Get parameters from the request
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    employee_id = request.GET.get('employee_id')

    # Set default date range to last 7 days if not provided
    if not start_date:
        start_date = (timezone.now() - timedelta(days=7)).date()
    else:
        start_date = datetime.strptime(start_date, '%Y-%m-%d').date()

    if not end_date:
        end_date = timezone.now().date()
    else:
        end_date = datetime.strptime(end_date, '%Y-%m-%d').date()

    # Create datetime range for exact date filtering
    start_datetime = timezone.make_aware(datetime.combine(start_date, datetime.min.time()))
    end_datetime = timezone.make_aware(datetime.combine(end_date, datetime.max.time()))

    # Base query for attendance data
    attendance_data = Attendance.objects.filter(
        check_in_timestamp__range=(start_datetime, end_datetime),
        employee__isnull=False
    ).select_related('employee')

    # Filter by employee ID if provided
    if employee_id:
        attendance_data = attendance_data.filter(employee__employee_id=employee_id)

    employee_attendance = []
    for attendance in attendance_data:
        employee_attendance.append({
            'id_number': attendance.employee.employee_id,
            'name': attendance.employee.name,
            'department': attendance.employee.department,
            'date': attendance.check_in_timestamp.date(),
            'time_in': attendance.check_in_timestamp.time(),
            'time_out': attendance.check_out_timestamp.time() if attendance.check_out_timestamp else None
        })

    context = {
        'start_date': start_date,
        'end_date': end_date,
        'attendance_data': employee_attendance,
        'employee_id': employee_id,
    }

    # Render the HTML template
    template = get_template('employee_pdf_report.html')
    html = template.render(context)

    # Create a PDF
    result = BytesIO()
    pdf = pisa.pisaDocument(BytesIO(html.encode("UTF-8")), result)
    
    if not pdf.err:
        response = HttpResponse(result.getvalue(), content_type='application/pdf')
        response['Content-Disposition'] = f'inline; filename="employee_attendance_report_{start_date}_to_{end_date}.pdf"'
        return response
    return HttpResponse('Error Rendering PDF', status=400)

@login_required
@user_passes_test(is_admin)
def generate_pdf_report(request):
    # Get parameters from the request
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    search_query = request.GET.get('search', '')
    attendance_type = request.GET.get('attendance_type', 'all')

    # Set default date range to last 7 days if not provided
    if not start_date:
        start_date = (timezone.now() - timedelta(days=7)).date()
    else:
        start_date = datetime.strptime(start_date, '%Y-%m-%d').date()

    if not end_date:
        end_date = timezone.now().date()
    else:
        end_date = datetime.strptime(end_date, '%Y-%m-%d').date()

    # Create datetime range for exact date filtering
    start_datetime = timezone.make_aware(datetime.combine(start_date, datetime.min.time()))
    end_datetime = timezone.make_aware(datetime.combine(end_date, datetime.max.time()))

    # Initialize attendance data lists
    student_attendance = []
    employee_attendance = []
    visitor_attendance = []

    # Only fetch the selected attendance type data
    if attendance_type in ['all', 'student']:
        student_records = Attendance.objects.filter(
            check_in_timestamp__range=(start_datetime, end_datetime),
            student__isnull=False
        ).select_related('student')

        if search_query:
            student_records = student_records.filter(
                Q(student__name__icontains=search_query) | 
                Q(student__student_id__icontains=search_query)
            )

        for record in student_records:
            student_attendance.append({
                'name': record.student.name,
                'id_number': record.student.student_id,
                'course': record.student.course,
                'date': record.check_in_timestamp.date(),
                'time_in': record.check_in_timestamp,
                'time_out': record.check_out_timestamp
            })

    if attendance_type in ['all', 'employee']:
        employee_records = Attendance.objects.filter(
            check_in_timestamp__range=(start_datetime, end_datetime),
            employee__isnull=False
        ).select_related('employee')

        if search_query:
            employee_records = employee_records.filter(
                Q(employee__name__icontains=search_query) | 
                Q(employee__employee_id__icontains=search_query)
            )

        for record in employee_records:
            employee_attendance.append({
                'name': record.employee.name,
                'id_number': record.employee.employee_id,
                'department': record.employee.department,
                'date': record.check_in_timestamp.date(),
                'time_in': record.check_in_timestamp,
                'time_out': record.check_out_timestamp
            })

    if attendance_type in ['all', 'visitor']:
        visitor_records = Visitor.objects.filter(
            time_in__range=(start_datetime, end_datetime)
        )

        if search_query:
            visitor_records = visitor_records.filter(
                Q(name__icontains=search_query) |
                Q(contact_info__icontains=search_query)
            )

        for visitor in visitor_records:
            visitor_attendance.append({
                'name': visitor.name,
                'contact_info': visitor.contact_info,
                'purpose': visitor.purpose,
                'qr_code_id': visitor.qr_code.code_id if visitor.qr_code else 'N/A',
                'date': visitor.time_in.date(),
                'time_in': visitor.time_in,
                'time_out': visitor.time_out
            })

    # Sort all attendance lists by date and time
    student_attendance.sort(key=lambda x: (x['date'], x['time_in']))
    employee_attendance.sort(key=lambda x: (x['date'], x['time_in']))
    visitor_attendance.sort(key=lambda x: (x['date'], x['time_in']))

    # Prepare context for the template
    context = {
        'start_date': start_date,
        'end_date': end_date,
        'search_query': search_query,
        'attendance_type': attendance_type,
        'student_attendance': student_attendance if attendance_type in ['all', 'student'] else [],
        'employee_attendance': employee_attendance if attendance_type in ['all', 'employee'] else [],
        'visitor_attendance': visitor_attendance if attendance_type in ['all', 'visitor'] else [],
    }

    # Render the HTML template
    template = get_template('pdf_report.html')
    html = template.render(context)

    # Create a PDF
    result = BytesIO()
    pdf = pisa.pisaDocument(BytesIO(html.encode("UTF-8")), result)
    
    if not pdf.err:
        response = HttpResponse(result.getvalue(), content_type='application/pdf')
        response['Content-Disposition'] = f'inline; filename="attendance_report_{start_date}_to_{end_date}.pdf"'
        return response
    return HttpResponse('Error Rendering PDF', status=400)




@login_required
@user_passes_test(is_admin)
def calendar_events(request):
    start = request.GET.get('start')
    end = request.GET.get('end')
    
    # Parse dates and make them timezone-aware
    start_date = parser.parse(start)
    end_date = parser.parse(end)
    
    # Ensure the dates are timezone-aware
    if timezone.is_naive(start_date):
        start_date = timezone.make_aware(start_date)
    if timezone.is_naive(end_date):
        end_date = timezone.make_aware(end_date)
    
    events = Event.objects.filter(start__range=(start_date, end_date))
    
    event_list = []
    for event in events:
        event_list.append({
            'id': event.id,
            'title': event.title,
            'start': event.start.isoformat(),
            'allDay': event.all_day,
        })
    
    return JsonResponse(event_list, safe=False)

@login_required
@user_passes_test(is_admin)
@csrf_exempt
def save_event(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        # Parse the date and make it timezone-aware
        naive_datetime = parser.parse(data['start'])
        if timezone.is_naive(naive_datetime):
            aware_datetime = timezone.make_aware(naive_datetime)
        else:
            aware_datetime = naive_datetime
            
        event = Event.objects.create(
            title=data['title'],
            start=aware_datetime,
            all_day=data['allDay']
        )
        return JsonResponse({'status': 'success', 'id': event.id})
    return JsonResponse({'status': 'error'}, status=400)

@login_required
@user_passes_test(is_admin)
@csrf_exempt
def delete_event(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        event_id = data.get('id')
        if not event_id:
            return JsonResponse({'status': 'error', 'message': 'No event ID provided'}, status=400)
        try:
            event = Event.objects.get(id=event_id)
            event.delete()
            return JsonResponse({'status': 'success'})
        except Event.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'Event not found'}, status=404)
        except ValueError:
            return JsonResponse({'status': 'error', 'message': 'Invalid event ID'}, status=400)
    return JsonResponse({'status': 'error', 'message': 'Invalid request method'}, status=400)

@login_required
@user_passes_test(is_security)
def visitor_check_in(request):
    if request.method == 'POST':
        # Get available QR code
        qr_code = QRCode.get_available_code()
        if not qr_code:
            messages.error(request, 'No QR codes available')
            return redirect('demons:visitors')
            
        # Create temporary visitor record
        temp_visitor = TempVisitor.objects.create(
            qr_code=qr_code,
            name=request.POST['name'],
            contact_info=request.POST['contact_info'],
            purpose=request.POST['purpose']
        )
        
        # Mark QR code as in use
        qr_code.is_active = False
        qr_code.save()
        
        messages.success(request, f'Visitor checked in with QR code {qr_code.code_id}')
        return redirect('demons:visitors')
    
    return redirect('demons:visitors')
    
@login_required
@user_passes_test(is_security)
def visitor_check_out(request, code_id):
    # Get temporary visitor record
    temp_visitor = get_object_or_404(TempVisitor, qr_code__code_id=code_id)
    
    # Move to permanent record
    visitor = temp_visitor.move_to_permanent()
    
    messages.success(request, f'Visitor {visitor.name} checked out successfully')
    return redirect('demons:visitors')

def csrf_failure(request, reason=""):
    print(f"CSRF Failure Reason: {reason}")
    print(f"Request Method: {request.method}")
    print(f"Request Headers: {request.headers}")
    return HttpResponseForbidden(f'CSRF verification failed. Reason: {reason}')

