from django.urls import path
from . import views

app_name = 'demons'

urlpatterns = [
    path('', views.home, name='home'),
    path('login/', views.user_login, name='login'),
    path('logout/', views.user_logout, name='logout'),
    path('admin-dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('security-dashboard/', views.security_dashboard, name='security_dashboard'),
    path('register-visitor/', views.register_visitor, name='register_visitor'),
    path('register-student/', views.register_student, name='register_student'),
    path('register-employee/', views.register_employee, name='register_employee'),
    path('scan/', views.scan, name='scan'),
    path('process_qr/', views.process_qr, name='process_qr'),
    path('get_recent_activity/', views.get_recent_activity, name='get_recent_activity'),
    path('users/', views.users, name='users'),
    path('add-user/', views.add_user, name='add_user'),
    path('visitors/', views.visitors, name='visitors'),
    path('settings/', views.settings, name='settings'),
    path('attendance-report/', views.attendance_report, name='attendance_report'),
    path('generate-pdf-report/', views.generate_pdf_report, name='generate_pdf_report'),
    path('calendar-events/', views.calendar_events, name='calendar_events'),
    path('save-event/', views.save_event, name='save_event'),
    path('delete-event/', views.delete_event, name='delete_event'),
    path('generate_employee_pdf_report/', views.generate_employee_pdf_report, name='generate_employee_pdf_report'),
    path('visitor-check-in/', views.visitor_check_in, name='visitor_check_in'),
    path('visitor-check-out/<str:code_id>/', views.visitor_check_out, name='visitor_check_out'),

]

