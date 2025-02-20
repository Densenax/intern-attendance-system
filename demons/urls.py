from django.urls import path
from . import views
from reports_views import generate_employee_csv_report, generate_employee_excel_report, generate_excel_report

app_name = 'demons'

urlpatterns = [
    path('', views.home, name='home'),
    path('login/', views.user_login, name='login'),
    path('logout/', views.user_logout, name='logout'),

    path('admin-dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('security-dashboard/', views.security_dashboard, name='security_dashboard'),

    path('register-student/', views.register_student, name='register_student'),
    path('register-employee/', views.register_employee, name='register_employee'),

    path('scan/', views.scan, name='scan'),
    path('process_qr/', views.process_qr, name='process_qr'),

    path('get_recent_activity/', views.get_recent_activity, name='get_recent_activity'),

    path('users/', views.users, name='users'),
    path('add-user/', views.add_user, name='add_user'),

    path('settings/', views.settings, name='settings'),

    path('attendance-report/', views.attendance_report, name='attendance_report'),
    path('generate-pdf-report/', views.generate_pdf_report, name='generate_pdf_report'),
    path('generate_employee_pdf_report/', views.generate_employee_pdf_report, name='generate_employee_pdf_report'),

    path('generate-excel-report/', generate_excel_report, name='generate_excel_report'),
    path('generate_employee_excel_report/', generate_employee_excel_report, name='generate_employee_excel_report'),
    path('generate_employee_csv_report/', generate_employee_csv_report, name='generate_employee_csv_report'),
    
    path('calendar-events/', views.calendar_events, name='calendar_events'),
    path('save-event/', views.save_event, name='save_event'),
    path('delete-event/', views.delete_event, name='delete_event'),  
]

