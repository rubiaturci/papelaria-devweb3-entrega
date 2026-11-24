from django.contrib import admin

from .models import Categoria, Contato, Produto, Servico

admin.site.site_header = "Ponto & Vírgula Papelaria"
admin.site.site_title = "Ponto & Vírgula"
admin.site.index_title = "Administração da loja"


@admin.register(Categoria)
class CategoriaAdmin(admin.ModelAdmin):
    list_display = ("nome", "ativo")
    list_filter = ("ativo",)
    search_fields = ("nome",)


@admin.register(Produto)
class ProdutoAdmin(admin.ModelAdmin):
    list_display = ("nome", "categoria", "preco", "estoque", "ativo")
    list_filter = ("categoria", "ativo")
    search_fields = ("nome", "descricao")


@admin.register(Servico)
class ServicoAdmin(admin.ModelAdmin):
    list_display = ("nome", "grupo", "ativo")
    list_filter = ("grupo", "ativo")
    search_fields = ("nome", "descricao")


@admin.register(Contato)
class ContatoAdmin(admin.ModelAdmin):
    list_display = ("nome", "email", "telefone", "enviado_em")
    search_fields = ("nome", "email", "mensagem")
