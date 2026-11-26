from django.shortcuts import render
from django.views.decorators.cache import never_cache


@never_cache
def formulario_recusado(request, reason=""):
    formularios = {"login", "cadastro", "novo_contato", "password_reset", "minha_conta", "alterar_senha"}
    rota = request.resolver_match.view_name if request.resolver_match else None
    if rota in formularios:
        destino = rota
        texto = "Abrir formulário novamente"
    elif request.user.is_authenticated:
        destino = "painel"
        texto = "Voltar ao Dashboard"
    else:
        destino = "inicio"
        texto = "Voltar ao início"

    return render(
        request,
        "formulario_recusado.html",
        {"destino": destino, "texto": texto},
        status=403,
    )
