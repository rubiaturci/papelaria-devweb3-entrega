from pathlib import Path

from django.conf import settings
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.core.management.base import BaseCommand

from loja.models import Produto


class Command(BaseCommand):
    help = "Copia as imagens dos produtos da pasta media/ para o armazenamento atual (banco em produção)."

    def handle(self, *args, **options):
        copiadas = 0
        for produto in Produto.objects.exclude(imagem="").exclude(imagem__isnull=True):
            nome = produto.imagem.name
            arquivo = Path(settings.MEDIA_ROOT) / nome
            if not nome or default_storage.exists(nome) or not arquivo.is_file():
                continue
            default_storage.save(nome, ContentFile(arquivo.read_bytes()))
            copiadas += 1
        self.stdout.write(f"{copiadas} imagem(ns) copiada(s).")
