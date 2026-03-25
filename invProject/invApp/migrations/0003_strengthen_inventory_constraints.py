from django.conf import settings
from django.db import migrations, models
from django.db.models import Q


def delete_orphan_products(apps, schema_editor):
    Product = apps.get_model("invApp", "Product")
    Product.objects.filter(owner__isnull=True).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("invApp", "0002_alter_product_options_product_created_at_and_more"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.RunPython(delete_orphan_products, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="product",
            name="owner",
            field=models.ForeignKey(
                on_delete=models.deletion.CASCADE, to=settings.AUTH_USER_MODEL
            ),
        ),
        migrations.AlterField(
            model_name="product",
            name="price",
            field=models.DecimalField(decimal_places=2, max_digits=10),
        ),
        migrations.AlterField(
            model_name="product",
            name="quantity",
            field=models.PositiveIntegerField(),
        ),
        migrations.AddConstraint(
            model_name="category",
            constraint=models.UniqueConstraint(
                fields=("owner", "name"), name="uq_category_owner_name"
            ),
        ),
        migrations.AddConstraint(
            model_name="product",
            constraint=models.UniqueConstraint(
                fields=("owner", "sku"), name="uq_product_owner_sku"
            ),
        ),
        migrations.AddConstraint(
            model_name="product",
            constraint=models.CheckConstraint(
                condition=Q(price__gt=0), name="ck_product_price_gt_zero"
            ),
        ),
        migrations.AddConstraint(
            model_name="product",
            constraint=models.CheckConstraint(
                condition=Q(quantity__gte=0), name="ck_product_quantity_gte_zero"
            ),
        ),
        migrations.AlterUniqueTogether(
            name="category",
            unique_together=set(),
        ),
        migrations.AlterUniqueTogether(
            name="product",
            unique_together=set(),
        ),
    ]
