# Generated by Django 5.1.2 on 2024-11-02 02:29

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0003_remove_invoiceitem_total_invoiceitem_vat_rate'),
    ]

    operations = [
        migrations.AddField(
            model_name='invoiceitem',
            name='currency',
            field=models.CharField(choices=[('EUR', '€'), ('CHF', 'CHF')], default='EUR', max_length=3),
        ),
    ]
