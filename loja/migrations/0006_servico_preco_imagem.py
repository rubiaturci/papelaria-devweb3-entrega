from decimal import Decimal
from django.core.validators import MinValueValidator
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("loja", "0005_integrantes_midia")]

    operations = [
        migrations.AddField(
            model_name="servico", name="preco",
            field=models.DecimalField("preço", max_digits=10, decimal_places=2, blank=True, null=True,
                                      validators=[MinValueValidator(Decimal("0.01"))]),
        ),
        migrations.AddField(
            model_name="servico", name="imagem",
            field=models.ImageField(upload_to="servicos/", blank=True, null=True),
        ),
    ]
