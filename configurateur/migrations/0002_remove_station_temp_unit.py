# Generated by Django 3.2.10 on 2021-12-09 12:12

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('configurateur', '0001_initial'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='station',
            name='temp_unit',
        ),
    ]
