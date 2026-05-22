from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('cinema', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='booking',
            name='paybox_payment_id',
            field=models.CharField(
                blank=True, default='', max_length=50,
                verbose_name='Paybox Payment ID'
            ),
        ),
        migrations.AlterField(
            model_name='booking',
            name='address',
            field=models.CharField(
                blank=True, default='', max_length=300,
                verbose_name='Адрес'
            ),
        ),
    ]
