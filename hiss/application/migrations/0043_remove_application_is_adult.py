# Generated by Django 2.2.13 on 2020-11-04 03:30

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('application', '0042_auto_20201101_1904'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='application',
            name='is_adult',
        ),
    ]