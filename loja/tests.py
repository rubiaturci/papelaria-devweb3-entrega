from unittest.mock import patch

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from .models import Categoria, Contato, Produto


class BaseTest(TestCase):
    def setUp(self):
        self.categoria = Categoria.objects.create(nome="Cadernos")
        self.produto = Produto.objects.create(
            nome="Caderno Azul", preco="20.00", estoque=5, categoria=self.categoria
        )
        self.equipe = User.objects.create_user("equipe", password="senha-teste-123", is_staff=True)
        self.cliente = User.objects.create_user("cliente", password="senha-teste-123")


class PaginasPublicasTests(BaseTest):
    def test_paginas_abrem(self):
        for rota in ("inicio", "produtos", "novo_contato", "login", "cadastro"):
            with self.subTest(rota=rota):
                self.assertEqual(self.client.get(reverse(rota)).status_code, 200)

    def test_produto_inativo_nao_aparece(self):
        Produto.objects.create(nome="Escondido", preco="5.00", ativo=False, categoria=self.categoria)
        resposta = self.client.get(reverse("produtos"))
        self.assertContains(resposta, "Caderno Azul")
        self.assertNotContains(resposta, "Escondido")

    def test_filtros(self):
        barato = Produto.objects.create(nome="Lápis", preco="3.00", categoria=self.categoria)
        resposta = self.client.get(reverse("produtos"), {"busca": "lápis"})
        self.assertEqual(list(resposta.context["produtos"]), [barato])
        resposta = self.client.get(reverse("produtos"), {"preco": "acima50"})
        self.assertEqual(list(resposta.context["produtos"]), [])
        resposta = self.client.get(reverse("produtos"), {"ordem": "menor"})
        self.assertEqual(resposta.context["produtos"][0], barato)

    def test_categoria_invalida_nao_quebra(self):
        for valor in ("abc", "999999999999999999999999", "²"):
            with self.subTest(valor=valor):
                resposta = self.client.get(reverse("produtos"), {"categoria": valor})
                self.assertEqual(resposta.status_code, 200)

    def test_contato_e_salvo(self):
        dados = {"nome": "Ana", "telefone": "11999990000", "email": "ana@exemplo.com", "mensagem": "Oi"}
        self.client.post(reverse("novo_contato"), dados)
        self.assertEqual(Contato.objects.count(), 1)

    def test_contato_sem_campo_obrigatorio_e_recusado(self):
        dados = {"nome": "Ana", "email": "ana@exemplo.com", "mensagem": "Oi"}
        resposta = self.client.post(reverse("novo_contato"), dados)
        self.assertEqual(resposta.status_code, 200)
        self.assertEqual(Contato.objects.count(), 0)


class PermissoesTests(BaseTest):
    def test_visitante_e_cliente_nao_gerenciam(self):
        url = reverse("gerenciar_produtos")
        self.assertEqual(self.client.get(url).status_code, 302)
        self.client.force_login(self.cliente)
        self.assertEqual(self.client.get(url).status_code, 302)

    def test_excluir_exige_post(self):
        self.client.force_login(self.equipe)
        url = reverse("excluir_produto", args=[self.produto.id])
        self.assertEqual(self.client.get(url).status_code, 405)
        self.assertTrue(Produto.objects.filter(id=self.produto.id).exists())

    def test_cliente_nao_exclui(self):
        self.client.force_login(self.cliente)
        self.client.post(reverse("excluir_produto", args=[self.produto.id]))
        self.assertTrue(Produto.objects.filter(id=self.produto.id).exists())


class GerenciarProdutosTests(BaseTest):
    def setUp(self):
        super().setUp()
        self.client.force_login(self.equipe)

    def test_adicionar(self):
        dados = {"nome": "Borracha", "preco": "2.50", "estoque": 10,
                 "categoria": self.categoria.id, "ativo": "on"}
        resposta = self.client.post(reverse("adicionar_produto"), dados)
        self.assertRedirects(resposta, reverse("gerenciar_produtos"))
        self.assertTrue(Produto.objects.filter(nome="Borracha").exists())

    def test_preco_zero_e_recusado(self):
        dados = {"nome": "Grátis", "preco": "0", "estoque": 1, "categoria": self.categoria.id}
        resposta = self.client.post(reverse("adicionar_produto"), dados)
        self.assertEqual(resposta.status_code, 200)
        self.assertFalse(Produto.objects.filter(nome="Grátis").exists())

    def test_editar(self):
        dados = {"nome": "Caderno Verde", "preco": "21.00", "estoque": 5,
                 "categoria": self.categoria.id, "ativo": "on"}
        self.client.post(reverse("editar_produto", args=[self.produto.id]), dados)
        self.produto.refresh_from_db()
        self.assertEqual(self.produto.nome, "Caderno Verde")

    def test_excluir(self):
        self.client.post(reverse("excluir_produto", args=[self.produto.id]))
        self.assertFalse(Produto.objects.filter(id=self.produto.id).exists())


class IntegrantesTests(BaseTest):
    @patch("loja.views.get_supabase")
    def test_lista(self, cliente):
        tabela = cliente.return_value.table.return_value
        tabela.select.return_value.execute.return_value.data = [
            {"id": 1, "nome": "Rubia", "cargo": "Dev", "biografia": "", "foto_url": ""}
        ]
        self.assertContains(self.client.get(reverse("integrantes")), "Rubia")

    @patch("loja.views.get_supabase", side_effect=Exception("sem conexão"))
    def test_supabase_fora_do_ar_mostra_aviso(self, cliente):
        with self.assertLogs("loja.views", level="ERROR"):
            resposta = self.client.get(reverse("integrantes"))
        self.assertContains(resposta, "Não foi possível", status_code=503)
        self.assertEqual(self.client.get(reverse("produtos")).status_code, 200)

    @patch("loja.views.get_supabase")
    def test_adicionar(self, cliente):
        self.client.force_login(self.equipe)
        dados = {"nome": "Rubia", "cargo": "Dev", "biografia": "", "foto_url": ""}
        self.client.post(reverse("adicionar_integrante"), dados)
        cliente.return_value.table.return_value.insert.assert_called_once_with(dados)


class CategoriaApiTests(BaseTest):
    def test_lista_e_detalhe_publicos(self):
        self.assertEqual(self.client.get(reverse("categoria_api")).json()[0]["nome"], "Cadernos")
        url = reverse("categoria_api_detalhe", args=[self.categoria.id])
        self.assertEqual(self.client.get(url).json()["nome"], "Cadernos")

    def test_visitante_nao_altera(self):
        resposta = self.client.post(reverse("categoria_api"), {"nome": "Nova"})
        self.assertEqual(resposta.status_code, 403)

    def test_criar_com_login(self):
        self.client.force_login(self.equipe)
        resposta = self.client.post(reverse("categoria_api"), {"nome": "Nova"})
        self.assertEqual(resposta.status_code, 201)

    def test_categoria_com_produto_nao_e_excluida(self):
        self.client.force_login(self.equipe)
        url = reverse("categoria_api_detalhe", args=[self.categoria.id])
        self.assertEqual(self.client.delete(url).status_code, 409)
        self.assertTrue(Categoria.objects.filter(id=self.categoria.id).exists())

    def test_excluir_sem_id(self):
        self.client.force_login(self.equipe)
        self.assertEqual(self.client.delete(reverse("categoria_api")).status_code, 400)


class ServicosTests(TestCase):
    def test_pagina_mostra_servicos_iniciais(self):
        resposta = self.client.get(reverse("servicos"))
        self.assertEqual(resposta.status_code, 200)
        self.assertContains(resposta, "Plastificação")
        self.assertContains(resposta, "Acabamentos e Documentos")

    def test_servico_inativo_nao_aparece(self):
        from .models import Servico
        Servico.objects.create(grupo="Teste", nome="Oculto", ativo=False)
        self.assertNotContains(self.client.get(reverse("servicos")), "Oculto")


class RelatorioTests(TestCase):
    def setUp(self):
        self.equipe = User.objects.create_user("equipe", password="x", is_staff=True)
        categoria = Categoria.objects.create(nome="Canetas")
        Produto.objects.create(nome="Caneta", preco="2.00", estoque=3, categoria=categoria)
        Produto.objects.create(nome="Lápis", preco="1.50", estoque=100, categoria=categoria)

    def test_visitante_e_redirecionado(self):
        self.assertEqual(self.client.get(reverse("gerar_relatorio")).status_code, 302)

    def test_equipe_ve_relatorio(self):
        self.client.force_login(self.equipe)
        resposta = self.client.get(reverse("gerar_relatorio"))
        self.assertEqual(resposta.status_code, 200)
        self.assertContains(resposta, "R$ 156,00")
        self.assertContains(resposta, "Serviços por tipo")
        self.assertContains(resposta, "Plastificação")
        self.assertEqual([p.nome for p in resposta.context["estoque_baixo"]], ["Caneta"])
