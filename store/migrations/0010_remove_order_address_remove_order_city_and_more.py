# Generated by Django 5.0.6 on 2024-06-06 09:50

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('store', '0009_rename_merchant_id_order_payment_intent'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='order',
            name='address',
        ),
        migrations.RemoveField(
            model_name='order',
            name='city',
        ),
        migrations.RemoveField(
            model_name='order',
            name='zipcode',
        ),
    ]
