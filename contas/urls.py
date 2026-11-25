from django.contrib.auth import views as auth_views
from django.urls import path, reverse_lazy

from . import views

urlpatterns = [
    path("entrar/", views.EntrarView.as_view(), name="login"),
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
    # Recuperação de senha (esqueci minha senha)
    path(
        "recuperar-senha/",
        auth_views.PasswordResetView.as_view(
            template_name="senha_reset_form.html",
            email_template_name="senha_reset_email.txt",
            subject_template_name="senha_reset_assunto.txt",
        ),
        name="password_reset",
    ),
    path(
        "recuperar-senha/enviado/",
        auth_views.PasswordResetDoneView.as_view(template_name="senha_reset_enviado.html"),
        name="password_reset_done",
    ),
    path(
        "recuperar-senha/<uidb64>/<token>/",
        auth_views.PasswordResetConfirmView.as_view(template_name="senha_reset_confirmar.html"),
        name="password_reset_confirm",
    ),
    path(
        "recuperar-senha/concluido/",
        auth_views.PasswordResetCompleteView.as_view(template_name="senha_reset_concluido.html"),
        name="password_reset_complete",
    ),
]
