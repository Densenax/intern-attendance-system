from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.html import format_html
from .models import User, Student, Employee, Visitor, Attendance

class CustomUserAdmin(UserAdmin):
    list_display = ('username', 'email', 'first_name', 'last_name', 'role', 'is_staff', 'is_superuser')
    list_filter = ('role', 'is_staff', 'is_superuser')
    fieldsets = UserAdmin.fieldsets + (
        ('Role', {'fields': ('role',)}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Role', {'fields': ('role',)}),
    )

class StudentAdmin(admin.ModelAdmin):
    list_display = ('name', 'student_id', 'course', 'qr_code_image')
    list_filter = ('course',)
    search_fields = ('name', 'student_id', 'contact_info')

    def qr_code_image(self, obj):
        if obj.qr_code:
            return format_html('<img src="{}" width="50" height="50" />', obj.qr_code.url)
        return "No image"

    qr_code_image.short_description = 'QR Code'

class EmployeeAdmin(admin.ModelAdmin):
    list_display = ('name', 'employee_id', 'department', 'qr_code_image')
    list_filter = ('department',)
    search_fields = ('name', 'employee_id', 'contact_info')

    def qr_code_image(self, obj):
        if obj.qr_code:
            return format_html('<img src="{}" width="50" height="50" />', obj.qr_code.url)
        return "No image"

    qr_code_image.short_description = 'QR Code'

class VisitorAdmin(admin.ModelAdmin):
    list_display = ('name', 'contact_info', 'purpose', 'qr_code_id', 'time_in', 'time_out')
    search_fields = ('name', 'contact_info', 'purpose')

    def qr_code_id(self, obj):
        return obj.qr_code.code_id if obj.qr_code else 'No QR Code'
    qr_code_id.short_description = 'QR Code ID'

class AttendanceAdmin(admin.ModelAdmin):
    list_display = ('get_name', 'get_type', 'check_in_timestamp', 'check_out_timestamp')
    list_filter = ('check_in_timestamp', 'check_out_timestamp')
    search_fields = ('student__name', 'employee__name', 'visitor__name')

    def get_name(self, obj):
        if obj.student:
            return obj.student.name
        elif obj.employee:
            return obj.employee.name
        return obj.visitor.name
    get_name.short_description = 'Name'

    def get_type(self, obj):
        if obj.student:
            return 'Student'
        elif obj.employee:
            return 'Employee'
        return 'Visitor'
    get_type.short_description = 'Type'

admin.site.register(User, CustomUserAdmin)
admin.site.register(Student, StudentAdmin)
admin.site.register(Employee, EmployeeAdmin)
admin.site.register(Visitor, VisitorAdmin)
admin.site.register(Attendance, AttendanceAdmin)

class QRCodeAdmin(admin.ModelAdmin):
    list_display = ('code_id', 'is_active', 'is_registered', 'created_at')
    search_fields = ('code_id',)

class TempVisitorAdmin(admin.ModelAdmin):
    list_display = ('name', 'contact_info', 'purpose', 'qr_code_id', 'time_in', 'registered_at')
    search_fields = ('name', 'contact_info', 'purpose')

    def qr_code_id(self, obj):
        return obj.qr_code.code_id if obj.qr_code else 'No QR Code'
    qr_code_id.short_description = 'QR Code ID'
