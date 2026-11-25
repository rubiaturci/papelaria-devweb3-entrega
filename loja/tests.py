from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from django.urls import reverse

from .models import ArquivoMidia, Categoria, Contato, Integrante, Pedido, Produto, Servico


class BaseTest(TestCase):
    def setUp(self):
        api = patch('loja.views.buscar_produtos_api', return_value=[])
        api.start()
        self.addCleanup(api.stop)
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
    def setUp(self):
        super().setUp()
        self.integrante = Integrante.objects.create(nome="Mariana", cargo="QA", biografia="Testes")

    def test_equipe_aparece_nas_paginas_publicas(self):
        self.assertContains(self.client.get(reverse("integrantes")), "Mariana")
        self.assertContains(self.client.get(reverse("quem_somos")), "Mariana")

    def test_cliente_nao_gerencia_equipe(self):
        self.client.force_login(self.cliente)
        self.assertEqual(self.client.get(reverse("gerenciar_equipe")).status_code, 302)
        url = reverse("excluir_integrante", args=[self.integrante.id])
        self.client.post(url)
        self.assertTrue(Integrante.objects.filter(id=self.integrante.id).exists())

    def test_adicionar_editar_excluir(self):
        self.client.force_login(self.equipe)
        dados = {"nome": "Felipe", "cargo": "Dev", "biografia": "", "foto_url": "https://exemplo.com/f.png"}
        self.client.post(reverse("adicionar_integrante"), dados)
        felipe = Integrante.objects.get(nome="Felipe")

        resposta = self.client.get(reverse("editar_integrante", args=[felipe.id]))
        self.assertContains(resposta, 'value="Felipe"')
        dados["nome"] = "Felipe Lima"
        self.client.post(reverse("editar_integrante", args=[felipe.id]), dados)
        felipe.refresh_from_db()
        self.assertEqual(felipe.nome, "Felipe Lima")

        self.client.post(reverse("excluir_integrante", args=[felipe.id]))
        self.assertFalse(Integrante.objects.filter(id=felipe.id).exists())


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


    def test_login_admin_leva_ao_django_admin(self):
        resposta = self.client.post(
            reverse("login"), {"username": "equipe", "password": "senha-teste-123"}
        )
        self.assertRedirects(resposta, reverse("admin:index"), fetch_redirect_response=False)


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


class RelatorioSituacaoTests(BaseTest):
    def test_ativos_e_inativos_vem_do_banco(self):
        Produto.objects.create(nome="Velho", preco="1.00", ativo=False, categoria=self.categoria)
        self.client.force_login(self.equipe)
        resposta = self.client.get(reverse("gerar_relatorio"))
        self.assertEqual(resposta.context["grafico_produtos_situacao"], [1, 1])
        self.assertEqual(resposta.context["total_inativos"], 1)
        self.assertContains(resposta, 'id="graficosituacao"')


class ServicosGerenciarTests(BaseTest):
    def test_cliente_nao_gerencia_servicos(self):
        self.client.force_login(self.cliente)
        self.assertEqual(self.client.get(reverse("gerenciar_servicos")).status_code, 302)

    def test_crud_e_filtros(self):
        self.client.force_login(self.equipe)
        dados = {"nome": "Teste impressão", "grupo": "Teste", "descricao": "Exemplo", "ativo": "on"}
        self.assertRedirects(self.client.post(reverse("adicionar_servico"), dados), reverse("gerenciar_servicos"))
        servico = Servico.objects.get(nome=dados["nome"])
        resposta = self.client.get(reverse("gerenciar_servicos"), {"grupo": "Teste", "situacao": "ativo"})
        self.assertEqual(list(resposta.context["servicos"]), [servico])
        dados["nome"] = "Teste atualizado"
        dados.pop("ativo")
        self.client.post(reverse("editar_servico", args=[servico.id]), dados)
        servico.refresh_from_db()
        self.assertEqual(servico.nome, "Teste atualizado")
        self.assertFalse(servico.ativo)
        url = reverse("excluir_servico", args=[servico.id])
        self.assertEqual(self.client.get(url).status_code, 405)
        self.client.post(url)
        self.assertFalse(Servico.objects.filter(pk=servico.pk).exists())

    def test_relatorio_servicos_usa_banco(self):
        self.client.force_login(self.equipe)
        Servico.objects.create(nome="Teste de relatório", grupo="Teste relatório", ativo=False)
        resposta = self.client.get(reverse("gerar_relatorio"))
        self.assertEqual(resposta.context["total_servicos_cadastrados"], Servico.objects.count())
        self.assertEqual(resposta.context["total_servicos_inativos"], Servico.objects.filter(ativo=False).count())
        self.assertIn("Teste relatório", resposta.context["grafico_grupos_servicos_labels"])

    def test_cliente_nao_altera_categoria(self):
        self.client.force_login(self.cliente)
        self.assertEqual(self.client.post(reverse("categoria_api"), {"nome": "Indevida"}).status_code, 403)


class PersistenciaMidiaTests(TestCase):
    def test_imagem_lida_do_banco_por_nova_instancia(self):
        from django.core.files.base import ContentFile
        from .storage import BancoDeDadosStorage
        nome = BancoDeDadosStorage().save("produtos/teste.png", ContentFile(b"imagem de teste"))
        self.assertTrue(ArquivoMidia.objects.filter(nome=nome).exists())
        with BancoDeDadosStorage().open(nome) as arquivo:
            self.assertEqual(arquivo.read(), b"imagem de teste")
        resposta = self.client.get(reverse("midia", args=[nome]))
        self.assertEqual(resposta.content, b"imagem de teste")


class AcabamentoRelatorioTests(BaseTest):
    def test_secoes_expansiveis_e_valor_formatado(self):
        self.client.force_login(self.equipe)
        self.produto.preco = Decimal("1822.20")
        self.produto.save()
        resposta = self.client.get(reverse("gerar_relatorio"))
        self.assertContains(resposta, 'id="relatorio-produtos"')
        self.assertContains(resposta, 'id="graficogruposservicos"')
        self.assertContains(resposta, "R$ 9.111,00")
        self.assertContains(resposta, "Serviços por tipo")

    def test_avatares_distintos_nas_paginas(self):
        nomes = ["Ana Souza", "Bruno Oliveira", "Carla Mendes"]
        integrantes = [Integrante.objects.create(nome=nome, cargo="Equipe") for nome in nomes]
        self.assertEqual(len({i.avatar_padrao for i in integrantes}), 3)
        from django.contrib.staticfiles import finders
        from PIL import Image
        for integrante in integrantes:
            self.assertTrue(integrante.avatar_padrao.endswith(".jpg"))
            caminho = finders.find(integrante.avatar_padrao)
            self.assertIsNotNone(caminho)
            with Image.open(caminho) as imagem:
                self.assertEqual(imagem.format, "JPEG")
                imagem.verify()
        self.client.force_login(self.equipe)
        for rota in ("quem_somos", "integrantes", "gerenciar_equipe"):
            resposta = self.client.get(reverse(rota))
            for integrante in integrantes:
                self.assertContains(resposta, integrante.avatar_padrao)
        resposta = self.client.get(reverse("editar_integrante", args=[integrantes[0].pk]))
        self.assertContains(resposta, integrantes[0].avatar_padrao)


class ServicosModeloOficialTests(BaseTest):
    def test_preco_filtros_e_indicadores(self):
        self.client.force_login(self.equipe)
        barato = Servico.objects.create(nome="Serviço teste barato", grupo="Teste oficial", preco="10.00")
        caro = Servico.objects.create(nome="Serviço teste caro", grupo="Teste oficial", preco="80.00")
        consulta = Servico.objects.create(nome="Serviço teste consulta", grupo="Teste oficial")
        resposta = self.client.get(reverse("gerenciar_servicos"), {"grupo": "Teste oficial", "ordem": "menor"})
        self.assertEqual(list(resposta.context["servicos"]), [barato, caro, consulta])
        self.assertEqual(resposta.context["resumo"]["menor"], Decimal("10.00"))
        self.assertEqual(resposta.context["resumo"]["maior"], Decimal("80.00"))
        resposta = self.client.get(reverse("gerenciar_servicos"), {"grupo": "Teste oficial", "preco": "consulta"})
        self.assertEqual(list(resposta.context["servicos"]), [consulta])
        resposta = self.client.get(reverse("gerenciar_servicos"), {"grupo": "Teste oficial", "preco": "ate20"})
        self.assertEqual(list(resposta.context["servicos"]), [barato])

    def test_servico_com_imagem_e_preco(self):
        from io import BytesIO
        from django.core.files.uploadedfile import SimpleUploadedFile
        from django.test import override_settings
        from PIL import Image
        self.client.force_login(self.equipe)
        buffer = BytesIO()
        Image.new("RGB", (12, 12), "green").save(buffer, format="PNG")
        imagem = SimpleUploadedFile("servico.png", buffer.getvalue(), content_type="image/png")
        armazenamento = {"default": {"BACKEND": "loja.storage.BancoDeDadosStorage"}, "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"}}
        with override_settings(STORAGES=armazenamento):
            resposta = self.client.post(reverse("adicionar_servico"), {
                "nome": "Serviço ilustrado", "grupo": "Teste oficial", "preco": "25.00",
                "imagem": imagem, "ativo": "on",
            })
            self.assertRedirects(resposta, reverse("gerenciar_servicos"))
            servico = Servico.objects.get(nome="Serviço ilustrado")
            self.assertEqual(servico.preco, Decimal("25.00"))
            self.assertTrue(ArquivoMidia.objects.filter(nome=servico.imagem.name).exists())
            self.assertContains(self.client.get(reverse("editar_servico", args=[servico.pk])), "Imagem atual")
            self.assertContains(self.client.get(reverse("servicos")), "R$ 25,00")

    def test_preco_negativo_recusado(self):
        self.client.force_login(self.equipe)
        resposta = self.client.post(reverse("adicionar_servico"), {"nome": "Preço inválido", "grupo": "Teste", "preco": "-1", "ativo": "on"})
        self.assertEqual(resposta.status_code, 200)
        self.assertFalse(Servico.objects.filter(nome="Preço inválido").exists())
