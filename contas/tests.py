import re

from django.contrib.auth.models import User
from django.test import Client, TestCase
from django.urls import reverse

from loja.models import Contato


class ContasTests(TestCase):
    def test_formulario_aberto_antes_do_login_pode_ser_reaberto(self):
        client = Client(enforce_csrf_checks=True)
        senha = "Senha-Teste-Fluxo-985"
        User.objects.create_user("cliente_fluxo", password=senha)
        contato = reverse("novo_contato")
        login = reverse("login")

        def token_da_pagina(url):
            resposta = client.get(url)
            return re.search(r'name="csrfmiddlewaretoken" value="([^"]+)"', resposta.text)[1]

        token_antigo = token_da_pagina(contato)
        resposta = client.post(login, {
            "username": "cliente_fluxo",
            "password": senha,
            "csrfmiddlewaretoken": token_da_pagina(login),
        })
        self.assertRedirects(resposta, reverse("painel"))

        dados = {
            "nome": "Pessoa de Teste",
            "email": "avaliacao@example.com",
            "telefone": "11912345678",
            "mensagem": "Mensagem de teste",
        }
        resposta = client.post(contato, {**dados, "csrfmiddlewaretoken": token_antigo})
        self.assertContains(
            resposta,
            f'<a class="botao" href="{contato}">Abrir formulário novamente</a>',
            status_code=403,
            html=True,
        )
        self.assertFalse(Contato.objects.exists())

        resposta = client.post(contato, {**dados, "csrfmiddlewaretoken": token_da_pagina(contato)})
        self.assertRedirects(resposta, reverse("inicio"))
        self.assertEqual(Contato.objects.count(), 1)

    def test_cadastro_cria_usuario_comum(self):
        dados = {
            "username": "nova",
            "email": "nova@exemplo.com",
            "password1": "UmaSenha-Forte-987",
            "password2": "UmaSenha-Forte-987",
        }
        resposta = self.client.post(reverse("cadastro"), dados)
        self.assertRedirects(resposta, reverse("painel"))
        self.assertFalse(User.objects.get(username="nova").is_staff)

    def test_cadastro_invalido_nao_cria(self):
        dados = {"username": "nova", "email": "x", "password1": "a", "password2": "b"}
        self.assertEqual(self.client.post(reverse("cadastro"), dados).status_code, 200)
        self.assertFalse(User.objects.exists())

    def test_minha_conta_exige_login(self):
        self.assertEqual(self.client.get(reverse("minha_conta")).status_code, 302)

    def test_minha_conta_recusa_email_invalido(self):
        usuario = User.objects.create_user("ana", "ana@exemplo.com", "senha-teste-123")
        self.client.force_login(usuario)
        self.client.post(reverse("minha_conta"), {"first_name": "Ana", "email": "invalido"})
        usuario.refresh_from_db()
        self.assertEqual(usuario.email, "ana@exemplo.com")

    def test_logout_por_post(self):
        usuario = User.objects.create_user("ana", password="senha-teste-123")
        self.client.force_login(usuario)
        self.assertEqual(self.client.post(reverse("logout")).status_code, 302)


    def test_recuperacao_nativa_ponta_a_ponta(self):
        from django.core import mail
        from urllib.parse import urlsplit
        usuario = User.objects.create_user("cliente_reset_teste", "reset@example.com", "Senha-Inicial-Teste-48")
        resposta = self.client.post(reverse("password_reset"), {"email": usuario.email})
        self.assertRedirects(resposta, reverse("password_reset_done"))
        self.assertEqual(len(mail.outbox), 1)
        link = next(l.strip() for l in mail.outbox[0].body.splitlines() if l.startswith("http"))
        resposta = self.client.get(urlsplit(link).path, follow=True)
        self.assertEqual(resposta.status_code, 200)
        nova = "Senha-Nova-Teste-839"
        resposta = self.client.post(resposta.request["PATH_INFO"], {"new_password1": nova, "new_password2": nova}, follow=True)
        self.assertRedirects(resposta, reverse("password_reset_complete"))
        usuario.refresh_from_db()
        self.assertTrue(usuario.check_password(nova))
        self.assertFalse(usuario.check_password("Senha-Inicial-Teste-48"))
        self.assertTrue(self.client.login(username=usuario.username, password=nova))

    def test_cliente_cadastrado_consegue_entrar_no_dashboard(self):
        dados = {"username": "cliente_novo", "email": "cliente@example.com", "password1": "Senha-Forte-Cadastro-83", "password2": "Senha-Forte-Cadastro-83"}
        self.assertRedirects(self.client.post(reverse("cadastro"), dados), reverse("painel"))
        usuario = User.objects.get(username="cliente_novo")
        self.assertTrue(usuario.is_active)
        self.assertFalse(usuario.is_staff)
        self.assertFalse(usuario.is_superuser)
        self.assertEqual(self.client.get(reverse("painel")).wsgi_request.user.pk, usuario.pk)
        self.client.logout()
        self.assertRedirects(self.client.post(reverse("login"), {"username": dados["username"], "password": dados["password1"]}), reverse("painel"))

    def test_cadastro_invalido_mostra_mensagem_clara(self):
        resposta = self.client.post(reverse("cadastro"), {"username": "cliente", "email": "cliente@example.com", "password1": "123", "password2": "456"})
        self.assertContains(resposta, "Não foi possível concluir o cadastro.")
        self.assertTrue(resposta.context["form"].errors)
        self.assertFalse(User.objects.filter(username="cliente").exists())

    def test_login_nao_retorna_ao_cadastro_mesmo_com_next(self):
        usuario = User.objects.create_user("cliente_fluxo", password="Senha-Teste-Fluxo-985")
        resposta = self.client.post(reverse("login"), {"username": usuario.username, "password": "Senha-Teste-Fluxo-985", "next": reverse("cadastro")}, follow=True)
        self.assertEqual(resposta.redirect_chain, [(reverse("painel"), 302)])
        self.assertEqual(resposta.wsgi_request.user.pk, usuario.pk)

    def test_cliente_autenticado_nao_volta_ao_cadastro(self):
        usuario = User.objects.create_user("cliente_ativo", password="Senha-Teste-Fluxo-985")
        self.client.force_login(usuario)
        self.assertRedirects(self.client.get(reverse("cadastro")), reverse("painel"))
        self.assertRedirects(self.client.get(reverse("login")), reverse("painel"))

    def test_admin_autenticado_mantem_destino_admin(self):
        usuario = User.objects.create_user("admin_fluxo", password="Senha-Teste-Fluxo-985", is_staff=True)
        self.client.force_login(usuario)
        self.assertRedirects(self.client.get(reverse("login")), reverse("admin:index"), fetch_redirect_response=False)
        self.assertRedirects(self.client.get(reverse("cadastro")), reverse("admin:index"), fetch_redirect_response=False)
