# Papelaria Ponto & Vírgula

Projeto de Desenvolvimento Web III. A aplicação simula uma papelaria com
catálogo, cadastro de clientes, registro de compras e área de gestão.

[Abrir o site publicado](https://papelaria-rphm.onrender.com)

## Roteiro de avaliação

1. Abra o catálogo para ver os produtos da papelaria, os filtros e a seção de itens de uma API externa.
2. Entre com a conta de cliente e abra o Dashboard para consultar o perfil e os pedidos.
3. Entre com a conta administrativa e abra o [Dashboard](https://papelaria-rphm.onrender.com/painel/) para acessar o gerenciamento e os relatórios.

Os acessos de teste são enviados por mensagem privada. Após um período sem
visitas, o Render pode levar cerca de um minuto para abrir o site. O banco do
Supabase pode ser pausado após uma semana de pouca atividade.

## Como rodar localmente

Com Python 3.13, execute os comandos abaixo na pasta do projeto. Se preferir,
crie e ative um ambiente virtual antes de instalar as dependências.

```sh
python -m pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Abra [http://127.0.0.1:8000/](http://127.0.0.1:8000/). As migrations criam um
banco SQLite local. Use o administrador que você criou para cadastrar dados de
exemplo. A instância publicada usa PostgreSQL no Supabase, configurado no Render.

O GitHub Actions verifica a configuração do Django, as migrations e a suíte de
testes. Para rodar as mesmas verificações localmente:

```sh
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py test
```

## Uso de IA

Usei ferramentas de IA sob minhas instruções para organizar o trabalho e apoiar
tarefas de implementação, revisão, testes e publicação. Eu defini o que
precisava ser feito e acompanhei as mudanças ao longo do projeto.
