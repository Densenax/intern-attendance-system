from django.core.management.base import BaseCommand
from demons.models import QRCode

class Command(BaseCommand):
    help = 'Generates initial QR codes'

    def handle(self, *args, **kwargs):
        # Generate 10 QR codes with IDs from 0001 to 0010
        for i in range(1, 11):
            code_id = f"{i:04d}"
            QRCode.objects.get_or_create(code_id=code_id)
        
        self.stdout.write(self.style.SUCCESS(f'Successfully generated {QRCode.objects.count()} QR codes'))

