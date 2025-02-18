from django.core.management.base import BaseCommand
from demons.models import Student, Employee, Visitor

class Command(BaseCommand):
    help = 'Regenerates QR codes for all users'

    def handle(self, *args, **options):
        for model in [Student, Employee, Visitor]:
            for user in model.objects.all():
                user.qr_code = None
                user.save()
                self.stdout.write(self.style.SUCCESS(f'Successfully regenerated QR code for {user}'))

