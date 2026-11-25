from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView
from django.shortcuts import redirect, render
from django.urls import reverse

from .forms import CadastroForm, PerfilForm


class EntrarView(LoginView):
    template_name = "login.html"

    def get_success_url(self):
        if self.request.user.is_staff:
            return reverse("admin:index")
        return super().get_success_url()


def cadastro(request):
    form = CadastroForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Cadastro feito! Agora é só entrar.")
        return redirect("login")
    return render(request, "cadastro.html", {"form": form})


@login_required
def minha_conta(request):
    form = PerfilForm(request.POST or None, instance=request.user)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Dados atualizados.")
        return redirect("minha_conta")
    return render(request, "minha_conta.html", {"form": form})
