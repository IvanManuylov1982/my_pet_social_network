# Generated by Django 2.2.9 on 2022-06-16 16:51

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('posts', '0002_auto_20220616_1209'),
    ]

    operations = [
        migrations.RenameField(
            model_name='group',
            old_name='descriptions',
            new_name='description',
        ),
        migrations.AlterField(
            model_name='group',
            name='title',
            field=models.CharField(max_length=200),
        ),
    ]
