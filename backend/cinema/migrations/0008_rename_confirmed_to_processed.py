from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('cinema', '0007_add_confirmed_by'),
    ]

    operations = [
        migrations.RenameField(
            model_name='booking',
            old_name='confirmed_by',
            new_name='processed_by',
        ),
        migrations.RenameField(
            model_name='booking',
            old_name='confirmed_at',
            new_name='processed_at',
        ),
        migrations.AlterField(
            model_name='booking',
            name='processed_by',
            field=models.ForeignKey(
                blank=True, null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='processed_bookings',
                to=settings.AUTH_USER_MODEL,
                verbose_name='Оплату обработал',
            ),
        ),
        migrations.AlterField(
            model_name='booking',
            name='processed_at',
            field=models.DateTimeField(
                blank=True, null=True, verbose_name='Время обработки оплаты',
            ),
        ),
    ]
