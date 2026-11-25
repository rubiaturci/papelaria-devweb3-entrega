"""Testes das funcionalidades da demonstração: painel, pedidos,
filtros do gerenciamento, equipe e relatório de situação."""

from decimal import Decimal
from unittest.mock import patch

from django.urls import reverse

from .models import Categoria, Pedido, Produto
from .tests import BaseTest


class PainelTests(BaseTest):
    def test_painel_exige_login(self):
        self.assertEqual(self.client.get(reverse("painel")).status_code, 302)

    def test_cliente_ve_so_seus_cards(self):
        self.client.force_login(self.cliente)
        resposta = self.client.get(reverse("painel"))
        self.assertContains(resposta, "Meus pedidos")
        self.assertContains(resposta, "Editar perfil")
        self.assertNotContains(resposta, "Gerenciar produtos")
        self.assertNotContains(resposta, "Acessar relatórios")

    def test_equipe_ve_seis_cards(self):
        self.client.force_login(self.equipe)
        resposta = self.client.get(reverse("painel"))
        for texto in (
            "Editar perfil",
            "Meus pedidos",
            "Gerenciar contatos",
            "Gerenciar produtos",
            "Gerenciar equipe",
            "Acessar relatórios",
        ):
            self.assertContains(resposta, texto)

    def test_login_leva_ao_painel(self):
        resposta = self.client.post(
            reverse("login"), {"username": "cliente", "password": "senha-teste-123"}
        )
        self.assertRedirects(resposta, reverse("painel"))


class PedidosTests(BaseTest):
    def test_comprar_exige_login_e_post(self):
        url = reverse("comprar", args=[self.produto.id])
        self.assertEqual(self.client.post(url).status_code, 302)
        self.assertEqual(Pedido.objects.count(), 0)
        self.client.force_login(self.cliente)
        self.assertEqual(self.client.get(url).status_code, 405)

    def test_compras_repetidas_e_total(self):
        outro = Produto.objects.create(nome="Caneta", preco="15.50", categoria=self.categoria)
        self.client.force_login(self.cliente)
        self.client.post(reverse("comprar", args=[self.produto.id]))
        self.client.post(reverse("comprar", args=[self.produto.id]))
        resposta = self.client.post(reverse("comprar", args=[outro.id]), follow=True)
        self.assertEqual(len(resposta.context["pedidos"]), 3)
        self.assertEqual(resposta.context["total"], Decimal("55.50"))
        self.assertContains(resposta, "R$ 55,50")

    def test_cada_usuario_ve_so_os_seus(self):
        self.client.force_login(self.equipe)
        self.client.post(reverse("comprar", args=[self.produto.id]))
        self.client.force_login(self.cliente)
        resposta = self.client.get(reverse("meus_pedidos"))
        self.assertEqual(len(resposta.context["pedidos"]), 0)
        self.assertEqual(resposta.context["total"], 0)

    def test_produto_inativo_nao_pode_ser_comprado(self):
        self.produto.ativo = False
        self.produto.save()
        self.client.force_login(self.cliente)
        resposta = self.client.post(reverse("comprar", args=[self.produto.id]))
        self.assertEqual(resposta.status_code, 404)

    def test_pedido_guarda_preco_da_compra(self):
        self.client.force_login(self.cliente)
        self.client.post(reverse("comprar", args=[self.produto.id]))
        self.produto.preco = "99.00"
        self.produto.save()
        self.assertEqual(str(Pedido.objects.get().preco), "20.00")

    def test_catalogo_tem_botao_comprar(self):
        self.assertContains(self.client.get(reverse("produtos")), "Comprar")


class GerenciarFiltrosTests(BaseTest):
    def setUp(self):
        super().setUp()
        outra = Categoria.objects.create(nome="Mochilas")
        Produto.objects.create(nome="Mochila", preco="120.00", categoria=outra)
        Produto.objects.create(nome="Borracha", preco="2.00", ativo=False, categoria=self.categoria)
        self.client.force_login(self.equipe)

    def nomes(self, parametros):
        resposta = self.client.get(reverse("gerenciar_produtos"), parametros)
        return [p.nome for p in resposta.context["produtos"]]

    def test_indicadores(self):
        resumo = self.client.get(reverse("gerenciar_produtos")).context["resumo"]
        self.assertEqual(resumo["total"], 3)
        self.assertEqual(resumo["menor"], Decimal("2.00"))
        self.assertEqual(resumo["maior"], Decimal("120.00"))
        self.assertEqual((resumo["ativos"], resumo["inativos"]), (2, 1))

    def test_busca_filtros_e_ordem(self):
        self.assertEqual(self.nomes({"busca": "moch"}), ["Mochila"])
        self.assertEqual(self.nomes({"preco": "ate20"}), ["Borracha", "Caderno Azul"])
        self.assertEqual(self.nomes({"ordem": "maior"})[0], "Mochila")
        self.assertEqual(
            self.nomes({"categoria": self.categoria.id, "ordem": "menor"}),
            ["Borracha", "Caderno Azul"],
        )

    def test_gerenciamento_mostra_inativos(self):
        self.assertContains(self.client.get(reverse("gerenciar_produtos")), "Borracha")


class EquipeGerenciarTests(BaseTest):
    @patch("loja.views.get_supabase")
    def test_tabela_e_quem_somos(self, cliente):
        dados = [{"id": 7, "nome": "Mariana", "cargo": "QA", "biografia": "Testes", "foto_url": ""}]
        consulta = cliente.return_value.table.return_value.select.return_value.order.return_value
        consulta.execute.return_value.data = dados
        self.assertContains(self.client.get(reverse("quem_somos")), "Mariana")
        self.client.force_login(self.equipe)
        self.assertContains(self.client.get(reverse("gerenciar_equipe")), "Mariana")

    def test_cliente_nao_gerencia_equipe(self):
        self.client.force_login(self.cliente)
        self.assertEqual(self.client.get(reverse("gerenciar_equipe")).status_code, 302)
        self.assertEqual(self.client.get(reverse("editar_integrante", args=[1])).status_code, 302)

    @patch("loja.views.get_supabase")
    def test_editar_carrega_e_salva(self, cliente):
        tabela = cliente.return_value.table.return_value
        tabela.select.return_value.eq.return_value.execute.return_value.data = [
            {"id": 7, "nome": "Mariana", "cargo": "QA", "biografia": "", "foto_url": ""}
        ]
        self.client.force_login(self.equipe)
        self.assertContains(self.client.get(reverse("editar_integrante", args=[7])), 'value="Mariana"')
        dados = {"nome": "Mariana Lima", "cargo": "QA", "biografia": "", "foto_url": ""}
        resposta = self.client.post(reverse("editar_integrante", args=[7]), dados)
        self.assertRedirects(resposta, reverse("gerenciar_equipe"), fetch_redirect_response=False)
        tabela.update.assert_called_once_with(dados)
        tabela.update.return_value.eq.assert_called_once_with("id", 7)


class RelatorioSituacaoTests(BaseTest):
    def test_ativos_e_inativos_vem_do_banco(self):
        Produto.objects.create(nome="Velho", preco="1.00", ativo=False, categoria=self.categoria)
        self.client.force_login(self.equipe)
        resposta = self.client.get(reverse("gerar_relatorio"))
        self.assertEqual(resposta.context["grafico_produtos_situacao"], [1, 1])
        self.assertEqual(resposta.context["total_inativos"], 1)
        self.assertContains(resposta, 'id="graficosituacao"')
