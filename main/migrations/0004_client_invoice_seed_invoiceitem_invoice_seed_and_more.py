# Generated by Django 5.0.2 on 2024-11-10 05:23

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0003_invoice_is_draft_invoiceseed_invoice_invoice_seed'),
    ]

    operations = [
        migrations.AddField(
            model_name='client',
            name='invoice_seed',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to='main.invoiceseed'),
        ),
        migrations.AddField(
            model_name='invoiceitem',
            name='invoice_seed',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to='main.invoiceseed'),
        ),
        migrations.AlterField(
            model_name='invoiceitem',
            name='invoice',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, related_name='items', to='main.invoice'),
        ),
    ]
