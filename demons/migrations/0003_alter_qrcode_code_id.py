# Generated by Django 5.1.4 on 2024-12-14 03:00

import uuid
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("demons", "0002_qrcode_qr_code_image"),
    ]

    operations = [
        migrations.AlterField(
            model_name="qrcode",
            name="code_id",
            field=models.UUIDField(default=uuid.uuid4, editable=False, unique=True),
        ),
    ]
