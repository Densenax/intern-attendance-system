import os
from django.core.management.base import BaseCommand
from django.conf import settings
from demons.models import QRCode

class Command(BaseCommand):
    help = 'Deletes existing QR codes and regenerates them'

    def handle(self, *args, **kwargs):
        # Delete existing QR code images
        qr_code_dir = os.path.join(settings.MEDIA_ROOT, 'qr_codes')
        if os.path.exists(qr_code_dir):
            for file in os.listdir(qr_code_dir):
                file_path = os.path.join(qr_code_dir, file)
                if os.path.isfile(file_path):
                    os.unlink(file_path)

        # Clear the QRCode table
        QRCode.objects.all().delete()

        # Regenerate QR codes
        for i in range(1, 11):  # Generate 10 new QR codes
            code_id = f"{i:04d}"  # This will create codes from 0001 to 0010
            QRCode.objects.create(code_id=code_id)

        self.stdout.write(self.style.SUCCESS(f'Successfully reset {QRCode.objects.count()} QR codes'))

