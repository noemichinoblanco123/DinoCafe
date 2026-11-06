# Generated for the caja -> cocina -> mesero workflow.
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


MESAS = [(numero, f"Mesa {numero}") for numero in range(1, 11)]


def mover_pedidos_sin_pago_a_pendiente(apps, schema_editor):
    Pedido = apps.get_model("pedidos", "Pedido")
    Pago = apps.get_model("pedidos", "Pago")
    ids_pagados = Pago.objects.values_list("pedido_id", flat=True)
    Pedido.objects.exclude(pk__in=ids_pagados).update(estado="PENDIENTE_PAGO")


class Migration(migrations.Migration):
    dependencies = [
        ("pedidos", "0002_pago_reembolso"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AlterField(
            model_name="pedido",
            name="estado",
            field=models.CharField(
                choices=[
                    ("PENDIENTE_PAGO", "Pendiente de pago"),
                    ("ESPERA", "En espera"),
                    ("EN_PREPARACION", "En preparación"),
                    ("LISTO", "Listo para entregar"),
                    ("ENTREGADO", "Entregado"),
                ],
                default="PENDIENTE_PAGO",
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name="pedido",
            name="mesa",
            field=models.PositiveSmallIntegerField(choices=MESAS, default=1),
        ),
        migrations.AddField(
            model_name="pedido",
            name="registrado_por",
            field=models.ForeignKey(
                blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL,
                related_name="pedidos_registrados", to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddField(
            model_name="pedido",
            name="preparado_por",
            field=models.ForeignKey(
                blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL,
                related_name="pedidos_iniciados", to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddField(
            model_name="pedido",
            name="listo_por",
            field=models.ForeignKey(
                blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL,
                related_name="pedidos_listos", to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddField(
            model_name="pedido",
            name="entregado_por",
            field=models.ForeignKey(
                blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL,
                related_name="pedidos_entregados", to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddField(
            model_name="pedido",
            name="en_preparacion_en",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="pedido",
            name="listo_en",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="pedido",
            name="entregado_en",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.RunPython(mover_pedidos_sin_pago_a_pendiente, migrations.RunPython.noop),
    ]
