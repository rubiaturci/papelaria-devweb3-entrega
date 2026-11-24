from django.db import migrations

SERVICOS = [
    ("Impressões e Cópias", "Xerox e cópias", "Cópias preto e branco ou coloridas."),
    ("Impressões e Cópias", "Impressão de arquivos", "A partir de pen drive, e-mail ou WhatsApp: boletos, currículos, trabalhos escolares, apostilas e notas fiscais."),
    ("Impressões e Cópias", "Impressão especial", "Em papel Opaline (para certificados), papel fotográfico e fotoadesivos."),
    ("Impressões e Cópias", "Impressão de grandes formatos", "Banners em papel ou lona (em estabelecimentos maiores)."),
    ("Acabamentos e Documentos", "Plastificação", "Proteção de documentos como certidões, cartões do SUS e avisos."),
    ("Acabamentos e Documentos", "Encadernação", "Encadernação simples com espiral (mola) preta ou transparente e capas de acetato para apostilas, TCCs e relatórios."),
    ("Acabamentos e Documentos", "Digitalização de documentos", "Envio de arquivos digitalizados por e-mail ou salvos em mídia."),
    ("Serviços Administrativos e de Apoio", "Elaboração e digitação", "Criação ou ajuste de currículos, cartas, contratos simples e declarações."),
    ("Serviços Administrativos e de Apoio", "Serviços de internet e comunicação", "Envio de e-mails, emissão e atualização de boletos, segundas vias de contas (luz, água, telefone) e certidões negativas."),
    ("Serviços Administrativos e de Apoio", "Design gráfico básico", "Criação e impressão de cartões de visita e panfletos simples."),
    ("Papelaria Personalizada e Criativa", "Encomendas personalizadas", "Planners, agendas, cadernos artesanais, bloquinhos corporativos e itens personalizados para festas e lembrancinhas, sob encomenda."),
]


def criar_servicos(apps, schema_editor):
    Servico = apps.get_model("loja", "Servico")
    for grupo, nome, descricao in SERVICOS:
        Servico.objects.get_or_create(
            grupo=grupo, nome=nome, defaults={"descricao": descricao}
        )


def remover_servicos(apps, schema_editor):
    Servico = apps.get_model("loja", "Servico")
    Servico.objects.filter(
        grupo__in={grupo for grupo, _, _ in SERVICOS},
    ).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("loja", "0002_servico"),
    ]

    operations = [
        migrations.RunPython(criar_servicos, remover_servicos),
    ]
