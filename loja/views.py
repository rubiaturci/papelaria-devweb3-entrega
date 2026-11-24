import logging 
import requests

from django.contrib import messages
from django.contrib.auth.decorators import user_passes_test
from django.db.models import Count, DecimalField, F, ProtectedError, Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticatedOrReadOnly
from rest_framework.response import Response

from .forms import ContatoForm, IntegranteForm, ProdutoForm
from .models import Categoria, Contato, Produto, Servico
from .serializers import CategoriaSerializer
from .supabase_client import get_supabase

logger = logging.getLogger(__name__)

# Só usuários da equipe (is_staff) entram nas páginas de gerenciamento.
so_equipe = user_passes_test(lambda usuario: usuario.is_staff, login_url="login")


# Páginas públicas


def inicio(request):
    destaques = Produto.objects.filter(ativo=True).order_by("-criado_em")[:4]
    return render(request, "inicio.html", {"destaques": destaques})


def quem_somos(request):
    return render(request, "quem_somos.html")


def servicos(request):
    grupos = {}
    for servico in Servico.objects.filter(ativo=True):
        grupos.setdefault(servico.grupo, []).append(servico)
    return render(request, "servicos.html", {"grupos": grupos.items()})


def produtos(request):
    # Produtos vindos da API externa (exibidos acima do catálogo)
    try:
        resposta = requests.get("https://fakestoreapi.com/products", timeout=10)
        resposta.raise_for_status()
        produtos_api = resposta.json()
    except (requests.RequestException, ValueError):
        logger.exception("Falha ao buscar produtos da API externa")
        produtos_api = []

    lista = Produto.objects.filter(ativo=True).select_related("categoria")

    busca = request.GET.get("busca", "").strip()
    if busca:
        lista = lista.filter(nome__icontains=busca)

    categoria = request.GET.get("categoria", "")
    if categoria.isdecimal() and len(categoria) < 10:
        lista = lista.filter(categoria_id=categoria)

    preco = request.GET.get("preco", "")
    if preco == "ate20":
        lista = lista.filter(preco__lte=20)
    elif preco == "20a50":
        lista = lista.filter(preco__gt=20, preco__lte=50)
    elif preco == "acima50":
        lista = lista.filter(preco__gt=50)

    ordem = request.GET.get("ordem", "")
    if ordem == "menor":
        lista = lista.order_by("preco")
    elif ordem == "maior":
        lista = lista.order_by("-preco")

    categorias_com_total = list(
        Categoria.objects.filter(ativo=True).annotate(total=Count("produtos")).order_by("nome")
    )

    contexto = {
        "produtos": lista,
        "produtos_api": produtos_api,
        "categorias": categorias_com_total,
        "grafico_categorias_labels": [c.nome for c in categorias_com_total],
        "grafico_categorias_valores": [c.total for c in categorias_com_total],
        "busca": busca,
        "categoria": categoria,
        "preco": preco,
        "ordem": ordem,
    }
    return render(request, "produtos.html", contexto)


def produto_detalhe(request, id):
    produto = get_object_or_404(Produto, id=id, ativo=True)
    return render(request, "produto_detalhe.html", {"produto": produto})


def novo_contato(request):
    form = ContatoForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Mensagem enviada! Obrigada pelo contato.")
        return redirect("inicio")
    return render(request, "contato_form.html", {"form": form})


# Gerenciamento de produtos


@so_equipe
def gerenciar_produtos(request):
    lista = Produto.objects.select_related("categoria")
    return render(request, "gerenciar_produtos.html", {"produtos": lista})


@so_equipe
def adicionar_produto(request):
    form = ProdutoForm(request.POST or None, request.FILES or None)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Produto adicionado.")
        return redirect("gerenciar_produtos")
    return render(request, "produto_form.html", {"form": form, "titulo": "Adicionar produto"})


@so_equipe
def editar_produto(request, id):
    produto = get_object_or_404(Produto, id=id)
    form = ProdutoForm(request.POST or None, request.FILES or None, instance=produto)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Produto atualizado.")
        return redirect("gerenciar_produtos")
    return render(request, "produto_form.html", {"form": form, "titulo": "Editar produto"})


@so_equipe
@require_POST
def excluir_produto(request, id):
    produto = get_object_or_404(Produto, id=id)
    if produto.imagem:
        produto.imagem.delete(save=False)
    produto.delete()
    messages.success(request, "Produto excluído.")
    return redirect("gerenciar_produtos")


# Mensagens de contato


@so_equipe
def contatos(request):
    return render(request, "contatos.html", {"contatos": Contato.objects.all()})


@so_equipe
@require_POST
def excluir_contato(request, id):
    get_object_or_404(Contato, id=id).delete()
    messages.success(request, "Mensagem excluída.")
    return redirect("contatos")


# Integrantes (ficam no Supabase, as outras páginas usam SQLite)


def integrantes(request):
    try:
        resposta = get_supabase().table("integrantes").select("*").execute()
    except Exception:
        logger.exception("Falha ao consultar integrantes")
        erro = "Não foi possível carregar a equipe agora. Verifique a conexão com o Supabase."
        return render(request, "integrantes.html", {"erro": erro}, status=503)
    return render(request, "integrantes.html", {"integrantes": resposta.data})


@so_equipe
def adicionar_integrante(request):
    form = IntegranteForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        try:
            get_supabase().table("integrantes").insert(form.cleaned_data).execute()
        except Exception:
            logger.exception("Falha ao cadastrar integrante")
            form.add_error(None, "Não foi possível salvar. Verifique a conexão com o Supabase.")
        else:
            messages.success(request, "Integrante adicionado.")
            return redirect("integrantes")
    return render(request, "integrante_form.html", {"form": form})


@so_equipe
@require_POST
def excluir_integrante(request, id):
    try:
        get_supabase().table("integrantes").delete().eq("id", id).execute()
    except Exception:
        logger.exception("Falha ao excluir integrante")
        messages.error(request, "Não foi possível excluir. Tente novamente.")
    else:
        messages.success(request, "Integrante excluído.")
    return redirect("integrantes")


# API de categorias (leitura pública, alterações só com login)


@api_view(["GET", "POST", "DELETE"])
@permission_classes([IsAuthenticatedOrReadOnly])
def categoria_api(request, id=None):
    if request.method == "GET":
        if id is None:
            serializer = CategoriaSerializer(Categoria.objects.all(), many=True)
        else:
            serializer = CategoriaSerializer(get_object_or_404(Categoria, id=id))
        return Response(serializer.data)

    if request.method == "POST":
        serializer = CategoriaSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    if id is None:
        return Response(
            {"erro": "Informe o ID da categoria na URL."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    categoria = get_object_or_404(Categoria, id=id)
    try:
        categoria.delete()
    except ProtectedError:
        return Response(
            {"erro": "Esta categoria tem produtos e não pode ser excluída."},
            status=status.HTTP_409_CONFLICT,
        )
    return Response(status=status.HTTP_204_NO_CONTENT)


# Relatório de estoque (só equipe)


@so_equipe
def gerar_relatorio(request):
    produtos_ativos = Produto.objects.filter(ativo=True)
    valor_estoque = produtos_ativos.aggregate(
        total=Sum(
            F("preco") * F("estoque"),
            output_field=DecimalField(max_digits=14, decimal_places=2),
        )
    )["total"] or 0

    servicos_por_grupo = {}
    for servico in Servico.objects.filter(ativo=True).order_by("grupo", "nome"):
        servicos_por_grupo.setdefault(servico.grupo, []).append(servico)

    categorias_grafico = Categoria.objects.annotate(total=Count("produtos")).order_by("nome")

    contexto = {
        "grafico_categorias_labels": [c.nome for c in categorias_grafico],
        "grafico_categorias_valores": [c.total for c in categorias_grafico],
        "grafico_servicos_valores": [
            Servico.objects.filter(ativo=True).count(),
            Servico.objects.filter(ativo=False).count(),
        ],
        "servicos_por_grupo": servicos_por_grupo.items(),
        "total_produtos": Produto.objects.count(),
        "total_ativos": produtos_ativos.count(),
        "valor_estoque": valor_estoque,
        "estoque_baixo": produtos_ativos.filter(estoque__lte=5).order_by("estoque", "nome"),
        "por_categoria": Categoria.objects.annotate(total=Count("produtos")).order_by("-total", "nome"),
        "total_contatos": Contato.objects.count(),
        "total_servicos": Servico.objects.filter(ativo=True).count(),
    }
    return render(request, "relatorio.html", contexto)
