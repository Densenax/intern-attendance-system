# Imports - standard python modules
from datetime import datetime, timedelta
from io import BytesIO
import csv

# Imports - external packages. Pls install using 'pip install'
from xhtml2pdf import pisa
from pandas import DataFrame

# Imports - Django modules
from django.contrib.auth.decorators import login_required, user_passes_test
from django.db.models import Q
from django.http import HttpResponse
from django.shortcuts import render, redirect
from django.template.loader import get_template
from django.utils import timezone

# Imports - Custom Code
from .models import Student, Employee, Attendance
from .views import is_admin

#helper methods: export methods
def export_to_csv(data, filename="employee_attendance.csv"):
    if not data:
        print("No data to export.")
        return

    try:
        with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
            fieldnames = data[0].keys() if data else [] 
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

            writer.writeheader()
            writer.writerows(data)

        print(f"Data successfully exported to {filename}")
    except Exception as e:
        print(f"Error exporting to CSV: {e}")

def export_to_excel(data, filename="employee_attendance.xlsx", sheet_name="Attendance"):
    if not data:
        print("No data to export.")
        return

    try:
        df = DataFrame(data)
        df.to_excel(filename, sheet_name=sheet_name, index=False)
        print(f"Data successfully exported to {filename}, sheet '{sheet_name}'")
    except Exception as e:
        print(f"Error exporting to Excel: {e}")

#Reports -- Excel/CSV
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

    # Get student and employee counts from Attendance model
    student_count = Attendance.objects.filter(
        check_in_timestamp__range=(start_datetime, end_datetime),
        student__isnull=False
    ).values('student').distinct().count()
    
    employee_count = Attendance.objects.filter(
        check_in_timestamp__range=(start_datetime, end_datetime),
        employee__isnull=False
    ).values('employee').distinct().count()

    # Process attendance data for template
    student_attendance = []
    employee_attendance = []

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

    # Sort all attendance lists by date and time
    student_attendance.sort(key=lambda x: (x['date'], x['time_in']))
    employee_attendance.sort(key=lambda x: (x['date'], x['time_in']))

    context = {
        'start_date': start_date,
        'end_date': end_date,
        'search_query': search_query,
        'student_attendance': student_attendance,
        'employee_attendance': employee_attendance,
        'student_count': student_count,
        'employee_count': employee_count,
    }

    return render(request, 'attendance_report.html', context)

@login_required
@user_passes_test(is_admin)
def generate_employee_excel_report(request):
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

    export_to_excel(employee_attendance)

@login_required
@user_passes_test(is_admin)
def generate_employee_csv_report(request):
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

    export_to_csv(employee_attendance)

@login_required
@user_passes_test(is_admin)
def generate_excel_report(request):
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


    # Sort all attendance lists by date and time
    student_attendance.sort(key=lambda x: (x['date'], x['time_in']))
    employee_attendance.sort(key=lambda x: (x['date'], x['time_in']))

    # Prepare context for the template
    context = {
        'start_date': start_date,
        'end_date': end_date,
        'search_query': search_query,
        'attendance_type': attendance_type,
        'student_attendance': student_attendance if attendance_type in ['all', 'student'] else [],
        'employee_attendance': employee_attendance if attendance_type in ['all', 'employee'] else [],
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

