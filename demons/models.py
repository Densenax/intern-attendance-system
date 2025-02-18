import qrcode
from io import BytesIO
from django.core.files import File
from django.db import models
from django.contrib.auth.models import AbstractUser
import uuid
from django.utils import timezone

class User(AbstractUser):
    ADMIN = 'admin'
    SECURITY = 'security'
    ROLE_CHOICES = [
        (ADMIN, 'Admin'),
        (SECURITY, 'Security'),
    ]
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, null=True, blank=True)

    groups = models.ManyToManyField(
        'auth.Group',
        verbose_name='groups',
        blank=True,
        help_text='The groups this user belongs to.',
        related_name='demons_user_set',
        related_query_name='demons_user'
    )
    user_permissions = models.ManyToManyField(
        'auth.Permission',
        verbose_name='user permissions',
        blank=True,
        help_text='Specific permissions for this user.',
        related_name='demons_user_set',
        related_query_name='demons_user'
    )

    def __str__(self):
        return f"{self.username} ({self.get_role_display()})"

    def save(self, *args, **kwargs):
        if self.role == self.ADMIN:
            self.is_staff = True
        super().save(*args, **kwargs)

class QRCode(models.Model):
    code_id = models.CharField(max_length=4, unique=True)
    is_active = models.BooleanField(default=True)
    is_registered = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    qr_code_image = models.ImageField(upload_to='qr_codes/', blank=True, null=True)

    def __str__(self):
        return f"QR Code: {self.code_id}"

    @classmethod
    def get_available_code(cls):
        return cls.objects.filter(is_active=True, is_registered=False).first()

    def save(self, *args, **kwargs):
        if not self.qr_code_image:
            qr = qrcode.QRCode(version=1, box_size=10, border=5)
            qr.add_data(self.code_id)
            qr.make(fit=True)
            img = qr.make_image(fill_color="black", back_color="white")
            buffer = BytesIO()
            img.save(buffer, format='PNG')
            self.qr_code_image.save(f'qr_code_{self.code_id}.png', File(buffer), save=False)
        super().save(*args, **kwargs)





class BaseUser(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100)
    contact_info = models.CharField(max_length=100)
    qr_code = models.ImageField(upload_to='qr_codes/', null=True, blank=True)
    department = models.CharField(max_length=100, null=True, blank=True)
    profile_photo = models.ImageField(upload_to='profile_photos/', null=True, blank=True)

    class Meta:
        abstract = True

    def generate_qr_code(self):
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(str(self.id))
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        buffer = BytesIO()
        img.save(buffer, format='PNG')
        buffer.seek(0)
        file_name = f'{self.__class__.__name__.lower()}_{self.id}.png'
        self.qr_code.save(file_name, File(buffer), save=False)

    def save(self, *args, **kwargs):
        is_new = self._state.adding
        super().save(*args, **kwargs)
        if is_new or not self.qr_code:
            self.generate_qr_code()
            self.save(update_fields=['qr_code'])


class Student(BaseUser):
    student_id = models.CharField(max_length=20, unique=True)
    course = models.CharField(max_length=100, null=True, blank=True)

    def __str__(self):
        return f"Student - {self.name} ({self.student_id})"


class Employee(BaseUser):
    employee_id = models.CharField(max_length=20, unique=True)
    department = models.CharField(max_length=100, null=True, blank=True)
    def __str__(self):
        return f"Employee - {self.name} ({self.employee_id})"

class TempVisitor(models.Model):
    qr_code = models.OneToOneField(QRCode, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    contact_info = models.CharField(max_length=100)
    purpose = models.CharField(max_length=200)
    time_in = models.DateTimeField(null=True, blank=True)
    registered_at = models.DateTimeField(default=timezone.now)
    
    def __str__(self):
        return f"Temporary Visitor: {self.name}"

    def move_to_permanent(self):
        visitor = Visitor.objects.create(
            name=self.name,
            contact_info=self.contact_info,
            purpose=self.purpose,
            time_in=self.time_in or self.registered_at,
            time_out=timezone.now(),
            qr_code=self.qr_code
        )
        
        # Reset QR code status
        self.qr_code.is_active = True
        self.qr_code.is_registered = False
        self.qr_code.save()
        
        self.delete()
        return visitor

        

class Visitor(models.Model):
    name = models.CharField(max_length=100)
    contact_info = models.CharField(max_length=100)
    purpose = models.CharField(max_length=200)
    time_in = models.DateTimeField()
    time_out = models.DateTimeField(null=True, blank=True)
    qr_code = models.ForeignKey(QRCode, on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
        return f"Visitor: {self.name}"
    
class Attendance(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE, null=True, blank=True)
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, null=True, blank=True)
    visitor = models.ForeignKey(Visitor, on_delete=models.CASCADE, null=True, blank=True)
    check_in_timestamp = models.DateTimeField(auto_now_add=True)
    check_out_timestamp = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        if self.student:
            return f"Attendance - Student: {self.student.name}"
        elif self.employee:
            return f"Attendance - Employee: {self.employee.name}"
        return f"Attendance - Visitor: {self.visitor.name}"

    @classmethod
    def get_total_check_ins(cls):
        return cls.objects.count()

    @classmethod
    def get_total_check_outs(cls):
        return cls.objects.filter(check_out_timestamp__isnull=False).count()

    @classmethod
    def get_student_check_ins(cls):
        return cls.objects.filter(student__isnull=False).count()

    @classmethod
    def get_student_check_outs(cls):
        return cls.objects.filter(student__isnull=False, check_out_timestamp__isnull=False).count()

    @classmethod
    def get_employee_check_ins(cls):
        return cls.objects.filter(employee__isnull=False).count()

    @classmethod
    def get_employee_check_outs(cls):
        return cls.objects.filter(employee__isnull=False, check_out_timestamp__isnull=False).count()

    @classmethod
    def get_visitor_check_ins(cls):
        return cls.objects.filter(visitor__isnull=False).count()

    @classmethod
    def get_visitor_check_outs(cls):
        return cls.objects.filter(visitor__isnull=False, check_out_timestamp__isnull=False).count()
    
class Event(models.Model):
    title = models.CharField(max_length=200)
    start = models.DateTimeField()
    all_day = models.BooleanField(default=True)

    def __str__(self):
        return self.title


