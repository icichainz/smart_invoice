# Generated by Django 5.0.2 on 2024-11-12 17:01

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0011_alter_invoice_total_amount_alter_invoiceitem_amount_and_more'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='invoice',
            name='is_invoice_ongoing',
        ),
        migrations.AddField(
            model_name='invoice',
            name='is_closed',
            field=models.BooleanField(default=False),
        ),
        migrations.AlterField(
            model_name='invoice',
            name='total_amount_final',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=22),
        ),
    ]