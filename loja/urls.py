from django.urls import path

from . import views

urlpatterns = [
    path("", views.inicio, name="inicio"),
    path("quem-somos/", views.quem_somos, name="quem_somos"),
    path("produtos/", views.produtos, name="produtos"),
    path("produtos/<int:id>/", views.produto_detalhe, name="produto_detalhe"),
    path("produtos/<int:id>/comprar/", views.comprar, name="comprar"),
    path("painel/", views.painel, name="painel"),
    path("meus-pedidos/", views.meus_pedidos, name="meus_pedidos"),
    path("servicos/", views.servicos, name="servicos"),
    path("contato/", views.novo_contato, name="novo_contato"),
    path("equipe/", views.integrantes, name="integrantes"),
    # Gerenciamento
    path("gerenciar/servicos/", views.gerenciar_servicos, name="gerenciar_servicos"),
    path("gerenciar/servicos/novo/", views.adicionar_servico, name="adicionar_servico"),
    path("gerenciar/servicos/<int:id>/editar/", views.editar_servico, name="editar_servico"),
    path("gerenciar/servicos/<int:id>/excluir/", views.excluir_servico, name="excluir_servico"),
    path("gerenciar/produtos/", views.gerenciar_produtos, name="gerenciar_produtos"),
    path("gerenciar/produtos/novo/", views.adicionar_produto, name="adicionar_produto"),
    path("gerenciar/produtos/<int:id>/editar/", views.editar_produto, name="editar_produto"),
    path("gerenciar/produtos/<int:id>/excluir/", views.excluir_produto, name="excluir_produto"),
    path("gerenciar/contatos/", views.contatos, name="contatos"),
    path("gerenciar/contatos/<int:id>/excluir/", views.excluir_contato, name="excluir_contato"),
    path("gerenciar/equipe/", views.gerenciar_equipe, name="gerenciar_equipe"),
    path("gerenciar/equipe/<int:id>/editar/", views.editar_integrante, name="editar_integrante"),
    path("gerenciar/equipe/novo/", views.adicionar_integrante, name="adicionar_integrante"),
    path("gerenciar/equipe/<int:id>/excluir/", views.excluir_integrante, name="excluir_integrante"),
    # API
    path("api/categorias/", views.categoria_api, name="categoria_api"),
    path("api/categorias/<int:id>/", views.categoria_api, name="categoria_api_detalhe"),

    path("media/<path:nome>", views.midia, name="midia"),
    path('relatorios/', views.gerar_relatorio, name='gerar_relatorio'),


]
