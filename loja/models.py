from decimal import Decimal

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models


class Categoria(models.Model):
    nome = models.CharField(max_length=100, unique=True)
    descricao = models.TextField("descrição", blank=True)
    ativo = models.BooleanField(default=True)

    class Meta:
        ordering = ["nome"]

    def __str__(self):
        return self.nome


class Produto(models.Model):
    nome = models.CharField(max_length=100)
    descricao = models.TextField("descrição", blank=True)
    preco = models.DecimalField(
        "preço",
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))],
    )
    estoque = models.PositiveIntegerField(default=0)
    imagem = models.ImageField(upload_to="produtos/", blank=True, null=True)
    ativo = models.BooleanField(default=True)
    categoria = models.ForeignKey(
        Categoria, on_delete=models.PROTECT, related_name="produtos"
    )
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["nome"]

    def __str__(self):
        return self.nome


class Servico(models.Model):
    grupo = models.CharField("grupo", max_length=60)
    nome = models.CharField(max_length=100)
    descricao = models.TextField("descrição", blank=True)
    ativo = models.BooleanField(default=True)

    class Meta:
        ordering = ["grupo", "nome"]
        verbose_name = "serviço"
        verbose_name_plural = "serviços"

    def __str__(self):
        return self.nome


class Contato(models.Model):
    nome = models.CharField(max_length=100)
    email = models.EmailField("e-mail")
    telefone = models.CharField(max_length=20, blank=True)
    mensagem = models.TextField()
    enviado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-enviado_em"]

    def __str__(self):
        return f"{self.nome} ({self.email})"


class Pedido(models.Model):
    """Compra feita por um cliente no catálogo.

    Nome, descrição e preço são copiados do produto no momento da compra,
    para o histórico não mudar se o produto for editado ou excluído depois.
    """

    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="pedidos"
    )
    produto = models.ForeignKey(
        Produto, on_delete=models.SET_NULL, null=True, blank=True, related_name="pedidos"
    )
    nome = models.CharField(max_length=100)
    descricao = models.TextField("descrição", blank=True)
    preco = models.DecimalField("preço", max_digits=10, decimal_places=2)
    criado_em = models.DateTimeField("comprado em", auto_now_add=True)

    class Meta:
        ordering = ["-criado_em"]

    def __str__(self):
        return f"{self.nome} - {self.usuario}"


class Integrante(models.Model):
    """Integrante da equipe.

    No Supabase (produção) é a tabela public.integrantes, que já existia.
    Localmente (SQLite) a tabela é criada pela migration 0005.
    """

    nome = models.CharField(max_length=100)
    cargo = models.CharField(max_length=100)
    biografia = models.TextField(blank=True, default="")
    foto_url = models.TextField("URL da foto", blank=True, null=True)

    class Meta:
        db_table = "integrantes"
        ordering = ["id"]

    @property
    def avatar_padrao(self):
        """Retrato demonstrativo local; fotos válidas cadastradas têm prioridade."""
        nome = (self.nome or "").strip().casefold()
        avatares = {
            "ana souza": "ana",
            "bruno oliveira": "bruno",
            "carla mendes": "carla",
        }
        perfil = avatares.get(nome)
        return f"images/avatar-{perfil}.jpg" if perfil else "images/avatar-equipe.svg"

    def __str__(self):
        return self.nome


class ArquivoMidia(models.Model):
    """Imagem enviada pelo site, guardada no próprio banco (Postgres do Supabase).

    Assim as imagens não somem quando o Render reinicia ou faz um novo deploy.
    """

    nome = models.CharField(max_length=255, unique=True)
    conteudo = models.BinaryField()
    tipo = models.CharField(max_length=100, default="application/octet-stream")
    tamanho = models.PositiveIntegerField(default=0)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "arquivo de mídia"
        verbose_name_plural = "arquivos de mídia"

    def __str__(self):
        return self.nome
