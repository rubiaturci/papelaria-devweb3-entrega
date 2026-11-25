import logging

from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView
from django.shortcuts import redirect, render
from django.urls import reverse

from .forms import CadastroForm, PerfilForm

logger = logging.getLogger(__name__)


class EntrarView(LoginView):
    template_name = "login.html"
    redirect_authenticated_user = True

    def get_success_url(self):
        if self.request.user.is_staff:
            return reverse("admin:index")
        return reverse("painel")


def cadastro(request):
    if request.user.is_authenticated:
        return redirect("admin:index" if request.user.is_staff else "painel")
    form = CadastroForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        usuario = form.save()
        login(request, usuario)
        messages.success(request, "Cadastro concluído! Bem-vindo à papelaria.")
        return redirect("painel")
    if request.method == "POST":
        # Registra apenas os códigos de validação, nunca dados preenchidos.
        codigos = {campo: [erro.code for erro in erros] for campo, erros in form.errors.as_data().items()}
        logger.warning("Cadastro recusado: %s", codigos)
    return render(request, "cadastro.html", {"form": form})


@login_required
def minha_conta(request):
    form = PerfilForm(request.POST or None, instance=request.user)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Dados atualizados.")
        return redirect("minha_conta")
    return render(request, "minha_conta.html", {"form": form})
