from django.contrib.auth import views as auth_views
from django.urls import path, reverse_lazy

from . import views

urlpatterns = [
    path("entrar/", auth_views.LoginView.as_view(template_name="login.html"), name="login"),
    path("sair/", auth_views.LogoutView.as_view(), name="logout"),
    path("cadastro/", views.cadastro, name="cadastro"),
    path("minha-conta/", views.minha_conta, name="minha_conta"),
    path(
        "alterar-senha/",
        auth_views.PasswordChangeView.as_view(
            template_name="alterar_senha.html",
            success_url=reverse_lazy("minha_conta"),
        ),
        name="alterar_senha",
    ),
]
