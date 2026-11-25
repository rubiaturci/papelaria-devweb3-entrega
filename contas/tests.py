from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse


class ContasTests(TestCase):
    def test_cadastro_cria_usuario_comum(self):
        dados = {
            "username": "nova",
            "email": "nova@exemplo.com",
            "password1": "UmaSenha-Forte-987",
            "password2": "UmaSenha-Forte-987",
        }
        resposta = self.client.post(reverse("cadastro"), dados)
        self.assertRedirects(resposta, reverse("login"))
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
