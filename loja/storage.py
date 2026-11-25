"""Armazenamento das imagens enviadas no próprio banco de dados.

No Render (plano grátis) o disco é apagado a cada reinício ou deploy.
Guardando as imagens no Postgres do Supabase, elas ficam salvas junto com
os produtos. As imagens são entregues pela view ``loja.views.midia``.
"""

import mimetypes

from django.core.files.base import ContentFile
from django.core.files.storage import Storage
from django.urls import reverse
from django.utils.deconstruct import deconstructible


@deconstructible
class BancoDeDadosStorage(Storage):
    def _modelo(self):
        from .models import ArquivoMidia

        return ArquivoMidia

    def _open(self, name, mode="rb"):
        arquivo = self._modelo().objects.get(nome=name)
        return ContentFile(bytes(arquivo.conteudo), name=name)

    def _save(self, name, content):
        content.seek(0)
        dados = content.read()
        tipo = getattr(content, "content_type", None) or mimetypes.guess_type(name)[0]
        self._modelo().objects.create(
            nome=name,
            conteudo=dados,
            tipo=tipo or "application/octet-stream",
            tamanho=len(dados),
        )
        return name

    def exists(self, name):
        return self._modelo().objects.filter(nome=name).exists()

    def delete(self, name):
        self._modelo().objects.filter(nome=name).delete()

    def size(self, name):
        return self._modelo().objects.only("tamanho").get(nome=name).tamanho

    def url(self, name):
        return reverse("midia", args=[name])
