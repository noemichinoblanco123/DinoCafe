from django.db import migrations, models


def completar_rutas_de_imagen(apps, schema_editor):
    Categoria = apps.get_model("catalogo", "Categoria")
    Producto = apps.get_model("catalogo", "Producto")
    rutas_categoria = {
        "Bebidas": "/images/carrusel/bebidas.jpg",
        "Acompañamientos": "/images/carrusel/acompanamientos.jpg",
    }
    rutas_producto = {
        "Té": "te.jpeg", "Café": "cafe.jpeg", "Cocoa": "cocoa.jpeg",
        "Cocoa con leche": "cocoa-con-leche.jpeg", "Leche": "leche.jpeg",
        "Pan": "pan.jpeg", "Empanada": "empanada.jpeg",
        "Trozo de torta": "trozo-de-torta.jpeg", "Trozo de rollo": "trozo-de-rollo.jpeg",
        "Sándwich de huevo": "sandwich-de-huevo.jpeg",
    }
    for categoria in Categoria.objects.all():
        ruta = rutas_categoria.get(categoria.nombre)
        if ruta and not categoria.imagen_carrusel:
            Categoria.objects.filter(pk=categoria.pk).update(imagen_carrusel=ruta)
    for producto in Producto.objects.all():
        archivo = rutas_producto.get(producto.nombre)
        if archivo and not producto.imagen:
            Producto.objects.filter(pk=producto.pk).update(imagen=f"/images/productos/{archivo}")


class Migration(migrations.Migration):
    dependencies = [
        ("catalogo", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="categoria",
            name="imagen_carrusel",
            field=models.CharField(blank=True, default="", max_length=255),
        ),
        migrations.AddField(
            model_name="producto",
            name="imagen",
            field=models.CharField(blank=True, default="", max_length=255),
        ),
        migrations.AddField(
            model_name="producto",
            name="activo",
            field=models.BooleanField(default=True),
        ),
        migrations.RunPython(completar_rutas_de_imagen, migrations.RunPython.noop),
    ]
