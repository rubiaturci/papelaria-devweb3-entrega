import logging

import requests
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.core.cache import cache
from django.db.models import Count, DecimalField, F, Max, Min, ProtectedError, Q, Sum
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST
from django.views.static import serve
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticatedOrReadOnly
from rest_framework.response import Response

from .forms import ContatoForm, IntegranteForm, ProdutoForm, ServicoForm
from .models import ArquivoMidia, Categoria, Contato, Integrante, Pedido, Produto, Servico
from .serializers import CategoriaSerializer

logger = logging.getLogger(__name__)

# Só usuários da equipe (is_staff) entram nas páginas de gerenciamento.
so_equipe = user_passes_test(lambda usuario: usuario.is_staff, login_url="login")


# Páginas públicas


def inicio(request):
    destaques = Produto.objects.filter(ativo=True).order_by("-criado_em")[:4]
    return render(request, "inicio.html", {"destaques": destaques})


def quem_somos(request):
    return render(request, "quem_somos.html", {"integrantes": Integrante.objects.all()})


def servicos(request):
    grupos = {}
    for servico in Servico.objects.filter(ativo=True):
        grupos.setdefault(servico.grupo, []).append(servico)
    return render(request, "servicos.html", {"grupos": grupos.items()})


CABECALHOS_API = {"User-Agent": "Mozilla/5.0 (PapelariaPontoVirgula/1.0)", "Accept": "application/json"}


def buscar_produtos_api():
    """Busca produtos de uma API externa.

    Tenta a Fake Store API primeiro. Ela costuma bloquear servidores em nuvem
    (como o Render), então, se falhar, usa a DummyJSON como alternativa.
    O resultado fica em cache por 1 hora para a página não esperar a API sempre.
    """
    produtos_api = cache.get("produtos_api")
    if produtos_api is not None:
        return produtos_api

    try:
        resposta = requests.get("https://fakestoreapi.com/products", headers=CABECALHOS_API, timeout=6)
        resposta.raise_for_status()
        produtos_api = resposta.json()
    except (requests.RequestException, ValueError):
        logger.warning("Fake Store API indisponível, tentando DummyJSON")
        try:
            resposta = requests.get(
                "https://dummyjson.com/products?limit=20&select=title,price,category,thumbnail",
                headers=CABECALHOS_API,
                timeout=6,
            )
            resposta.raise_for_status()
            produtos_api = [
                {
                    "title": item["title"],
                    "price": item["price"],
                    "category": item["category"],
                    "image": item["thumbnail"],
                }
                for item in resposta.json()["products"]
            ]
        except (requests.RequestException, ValueError, KeyError):
            logger.exception("Falha ao buscar produtos das APIs externas")
            return []

    cache.set("produtos_api", produtos_api, 60 * 60)
    return produtos_api


FAIXAS_PRECO = [
    ("ate20", "Até R$ 20"),
    ("20a50", "R$ 20 - R$ 50"),
    ("acima50", "Acima de R$ 50"),
]
ORDENS = [("menor", "Menor preço"), ("maior", "Maior preço"), ("nome", "Nome")]


def filtrar_produtos(lista, parametros):
    """Aplica busca, categoria, faixa de preço e ordenação vindos da URL.

    Usado no catálogo público e no gerenciamento de produtos.
    """
    busca = parametros.get("busca", "").strip()
    if busca:
        lista = lista.filter(nome__icontains=busca)

    categoria = parametros.get("categoria", "")
    if categoria.isdecimal() and len(categoria) < 10:
        lista = lista.filter(categoria_id=categoria)

    preco = parametros.get("preco", "")
    if preco == "ate20":
        lista = lista.filter(preco__lte=20)
    elif preco == "20a50":
        lista = lista.filter(preco__gt=20, preco__lte=50)
    elif preco == "acima50":
        lista = lista.filter(preco__gt=50)

    ordem = parametros.get("ordem", "")
    if ordem == "menor":
        lista = lista.order_by("preco", "nome")
    elif ordem == "maior":
        lista = lista.order_by("-preco", "nome")
    elif ordem == "nome":
        lista = lista.order_by("nome")

    return lista, {"busca": busca, "categoria": categoria, "preco": preco, "ordem": ordem}


def produtos(request):
    # Produtos vindos da API externa (exibidos abaixo do catálogo)
    produtos_api = buscar_produtos_api()

    lista, filtros = filtrar_produtos(
        Produto.objects.filter(ativo=True).select_related("categoria"), request.GET
    )
    busca, categoria, preco, ordem = (
        filtros["busca"], filtros["categoria"], filtros["preco"], filtros["ordem"]
    )

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
    todos = Produto.objects.select_related("categoria")
    lista, filtros = filtrar_produtos(todos, request.GET)
    resumo = todos.aggregate(
        total=Count("id"),
        menor=Min("preco"),
        maior=Max("preco"),
        ativos=Count("id", filter=Q(ativo=True)),
        inativos=Count("id", filter=Q(ativo=False)),
    )
    contexto = {
        "produtos": lista,
        "resumo": resumo,
        "categorias": Categoria.objects.order_by("nome"),
        "faixas_preco": FAIXAS_PRECO,
        "ordens": ORDENS,
        **filtros,
    }
    return render(request, "gerenciar_produtos.html", contexto)


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


# Gerenciamento dos serviços informativos da papelaria


@so_equipe
def gerenciar_servicos(request):
    todos = Servico.objects.all()
    lista = todos
    busca = request.GET.get("busca", "").strip()
    grupo = request.GET.get("grupo", "")
    situacao = request.GET.get("situacao", "")
    if busca:
        lista = lista.filter(nome__icontains=busca)
    if grupo:
        lista = lista.filter(grupo=grupo)
    if situacao in ("ativo", "inativo"):
        lista = lista.filter(ativo=situacao == "ativo")
    return render(request, "gerenciar_servicos.html", {
        "servicos": lista,
        "grupos": todos.order_by("grupo").values_list("grupo", flat=True).distinct(),
        "total": todos.count(),
        "ativos": todos.filter(ativo=True).count(),
        "inativos": todos.filter(ativo=False).count(),
        "busca": busca, "grupo": grupo, "situacao": situacao,
    })


@so_equipe
def adicionar_servico(request):
    form = ServicoForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Serviço cadastrado.")
        return redirect("gerenciar_servicos")
    return render(request, "servico_form.html", {"form": form, "titulo": "Novo serviço"})


@so_equipe
def editar_servico(request, id):
    servico = get_object_or_404(Servico, id=id)
    form = ServicoForm(request.POST or None, instance=servico)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Serviço atualizado.")
        return redirect("gerenciar_servicos")
    return render(request, "servico_form.html", {"form": form, "titulo": "Editar serviço"})


@so_equipe
@require_POST
def excluir_servico(request, id):
    get_object_or_404(Servico, id=id).delete()
    messages.success(request, "Serviço excluído.")
    return redirect("gerenciar_servicos")


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


# Integrantes (tabela "integrantes" no Postgres do Supabase)


def integrantes(request):
    return render(request, "integrantes.html", {"integrantes": Integrante.objects.all()})


@so_equipe
def gerenciar_equipe(request):
    return render(request, "gerenciar_equipe.html", {"integrantes": Integrante.objects.all()})


@so_equipe
def adicionar_integrante(request):
    form = IntegranteForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Integrante adicionado.")
        return redirect("gerenciar_equipe")
    return render(request, "integrante_form.html", {"form": form, "titulo": "Novo integrante"})


@so_equipe
def editar_integrante(request, id):
    integrante = get_object_or_404(Integrante, id=id)
    form = IntegranteForm(request.POST or None, instance=integrante)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Integrante atualizado.")
        return redirect("gerenciar_equipe")
    return render(request, "integrante_form.html", {"form": form, "titulo": "Editar integrante"})


@so_equipe
@require_POST
def excluir_integrante(request, id):
    get_object_or_404(Integrante, id=id).delete()
    messages.success(request, "Integrante excluído.")
    return redirect("gerenciar_equipe")


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

    if not request.user.is_staff:
        return Response({"erro": "Apenas a equipe pode alterar categorias."}, status=status.HTTP_403_FORBIDDEN)

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

    grupos_grafico = list(Servico.objects.values("grupo").annotate(total=Count("id")).order_by("grupo"))
    contexto = {
        "grafico_grupos_servicos_labels": [g["grupo"] for g in grupos_grafico],
        "grafico_grupos_servicos_valores": [g["total"] for g in grupos_grafico],
        "total_servicos_cadastrados": Servico.objects.count(),
        "total_servicos_inativos": Servico.objects.filter(ativo=False).count(),
        "grafico_categorias_labels": [c.nome for c in categorias_grafico],
        "grafico_categorias_valores": [c.total for c in categorias_grafico],
        "grafico_servicos_valores": [
            Servico.objects.filter(ativo=True).count(),
            Servico.objects.filter(ativo=False).count(),
        ],
        "servicos_por_grupo": servicos_por_grupo.items(),
        "total_produtos": Produto.objects.count(),
        "total_ativos": produtos_ativos.count(),
        "total_inativos": Produto.objects.filter(ativo=False).count(),
        "grafico_produtos_situacao": [
            produtos_ativos.count(),
            Produto.objects.filter(ativo=False).count(),
        ],
        "valor_estoque": valor_estoque,
        "estoque_baixo": produtos_ativos.filter(estoque__lte=5).order_by("estoque", "nome"),
        "por_categoria": Categoria.objects.annotate(total=Count("produtos")).order_by("-total", "nome"),
        "total_contatos": Contato.objects.count(),
        "total_servicos": Servico.objects.filter(ativo=True).count(),
    }
    return render(request, "relatorio.html", contexto)


# Painel do usuário e pedidos


@login_required
def painel(request):
    return render(request, "painel.html")


@login_required
@require_POST
def comprar(request, id):
    produto = get_object_or_404(Produto, id=id, ativo=True)
    Pedido.objects.create(
        usuario=request.user,
        produto=produto,
        nome=produto.nome,
        descricao=produto.descricao,
        preco=produto.preco,
    )
    messages.success(request, f"Compra registrada: {produto.nome}.")
    return redirect("meus_pedidos")


@login_required
def meus_pedidos(request):
    pedidos = Pedido.objects.filter(usuario=request.user).select_related("produto")
    total = pedidos.aggregate(total=Sum("preco"))["total"] or 0
    return render(request, "meus_pedidos.html", {"pedidos": pedidos, "total": total})


# Imagens enviadas (guardadas no banco; ver loja/storage.py)


def midia(request, nome):
    arquivo = ArquivoMidia.objects.filter(nome=nome).only("conteudo", "tipo").first()
    if arquivo is not None:
        resposta = HttpResponse(bytes(arquivo.conteudo), content_type=arquivo.tipo)
        resposta["Cache-Control"] = "public, max-age=86400"
        return resposta
    # Arquivos antigos que ainda estão na pasta media/ do projeto.
    return serve(request, nome, document_root=settings.MEDIA_ROOT)
