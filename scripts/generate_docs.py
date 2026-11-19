#!/usr/bin/env python3
"""Gera o relatório da aplicação atual e exporta a apresentação HTML."""
import argparse
import base64
import datetime
import io
import json
import subprocess
from html.parser import HTMLParser
from pathlib import Path
from xml.sax.saxutils import escape
from zoneinfo import ZoneInfo

from reportlab.graphics.shapes import Drawing, Line, Polygon, Rect, String
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    BaseDocTemplate, Frame, Image, PageBreak, PageTemplate, Paragraph,
    Preformatted, Spacer, Table, TableStyle,
)
from reportlab.platypus.tableofcontents import TableOfContents

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / 'docs'
QA = ROOT / 'artifacts' / 'qa'
WIDTH = A4[0] - 5 * cm
INK = colors.HexColor('#25303b')
GRAY = colors.HexColor('#697381')
LIGHT = colors.HexColor('#f6f7f9')


def register_fonts():
    # Incorpora fontes compatíveis com Times/Courier quando disponíveis no Linux.
    for directory in ('/usr/share/fonts/truetype/liberation', '/usr/share/fonts/truetype/liberation2'):
        folder = Path(directory)
        files = {
            'AcademicSerif': 'LiberationSerif-Regular.ttf',
            'AcademicSerif-Bold': 'LiberationSerif-Bold.ttf',
            'AcademicMono': 'LiberationMono-Regular.ttf',
        }
        if all((folder / filename).is_file() for filename in files.values()):
            for name, filename in files.items():
                pdfmetrics.registerFont(TTFont(name, str(folder / filename)))
            pdfmetrics.registerFontFamily('AcademicSerif', normal='AcademicSerif', bold='AcademicSerif-Bold')
            return 'AcademicSerif', 'AcademicSerif-Bold', 'AcademicMono'
    return 'Times-Roman', 'Times-Bold', 'Courier'


FONT_BODY, FONT_BOLD, FONT_CODE = register_fonts()
BODY = ParagraphStyle(
    'AcademicBody', fontName=FONT_BODY, fontSize=12, leading=18,
    alignment=TA_JUSTIFY, spaceAfter=9, firstLineIndent=1.25 * cm,
)
H1 = ParagraphStyle(
    'AcademicHeading', fontName=FONT_BOLD, fontSize=12, leading=18,
    spaceBefore=15, spaceAfter=12, keepWithNext=True,
)
H2 = ParagraphStyle(
    'AcademicSubheading', parent=H1, spaceBefore=12, spaceAfter=8,
)
CAPTION = ParagraphStyle(
    'AcademicCaption', fontName=FONT_BODY, fontSize=10, leading=13,
    alignment=TA_CENTER, spaceBefore=6, spaceAfter=10,
)
CELL = ParagraphStyle('TableCell', fontName=FONT_BODY, fontSize=9, leading=12)
HEADER = ParagraphStyle('TableHeader', parent=CELL, fontName=FONT_BOLD, textColor=colors.white)
COVER = ParagraphStyle('Cover', fontName=FONT_BODY, fontSize=12, leading=19, alignment=TA_CENTER)
CODE = ParagraphStyle(
    'Code', fontName=FONT_CODE, fontSize=8.2, leading=11,
    backColor=LIGHT, borderPadding=8, spaceBefore=8, spaceAfter=12,
)


def plain(value):
    return escape(str(value)).replace('\n', '<br/>')


def p(text, style=BODY):
    return Paragraph(text, style)


def paragraphs(story, *texts):
    story.extend(p(text) for text in texts)


def heading(story, title, level=1, new_page=False):
    if new_page:
        story.append(PageBreak())
    story.append(p(title, H1 if level == 1 else H2))


def table(headers, rows, widths):
    data = [[p(plain(value), HEADER) for value in headers]]
    data.extend([p(plain(value), CELL) for value in row] for row in rows)
    result = Table(data, colWidths=widths, repeatRows=1, hAlign='LEFT')
    result.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), INK),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('LEFTPADDING', (0, 0), (-1, -1), 7),
        ('RIGHTPADDING', (0, 0), (-1, -1), 7),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, LIGHT]),
        ('LINEBELOW', (0, 0), (-1, 0), .5, INK),
        ('LINEBELOW', (0, 1), (-1, -1), .25, colors.HexColor('#e5e7eb')),
    ]))
    return result


class AcademicDoc(BaseDocTemplate):
    def afterFlowable(self, flowable):
        if isinstance(flowable, Paragraph) and flowable.style.name in {H1.name, H2.name}:
            level = 0 if flowable.style.name == H1.name else 1
            key = f'heading-{self.seq.nextf("section")}'
            self.canv.bookmarkPage(key)
            self.canv.addOutlineEntry(flowable.getPlainText(), key, level=level, closed=False)
            self.notify('TOCEntry', (level, flowable.getPlainText(), self.page - 1, key))


def academic_page(canvas, doc):
    if doc.page >= 3:
        canvas.saveState()
        canvas.setFont(FONT_BODY, 10)
        canvas.drawRightString(A4[0] - 2 * cm, A4[1] - 2 * cm, str(doc.page - 1))
        canvas.restoreState()


def flowchart():
    drawing = Drawing(WIDTH, 300)
    labels = [
        'Iniciar o servidor C e abrir o SQLite',
        'Acessar a interface Angular no navegador',
        'Escolher Produtos, Vendas ou Relatórios',
        'Enviar a requisição HTTP para a API',
        'Validar, consultar ou gravar os dados',
        'Exibir o resultado e continuar ou encerrar',
    ]
    for index, label in enumerate(labels):
        y = 264 - index * 48
        drawing.add(Rect((WIDTH - 330) / 2, y, 330, 32, fillColor=LIGHT, strokeColor=GRAY, strokeWidth=.5))
        drawing.add(String(WIDTH / 2, y + 12, label, fontName=FONT_BODY, fontSize=10.5, textAnchor='middle', fillColor=INK))
        if index < len(labels) - 1:
            drawing.add(Line(WIDTH / 2, y, WIDTH / 2, y - 12, strokeColor=GRAY))
            drawing.add(Polygon([WIDTH / 2 - 3, y - 10, WIDTH / 2, y - 16, WIDTH / 2 + 3, y - 10], fillColor=GRAY, strokeColor=GRAY))
    return drawing


class PresentationImages(HTMLParser):
    def __init__(self):
        super().__init__()
        self.images = []

    def handle_starttag(self, tag, attrs):
        if tag == 'img':
            self.images.append(dict(attrs))

    def find(self, alt_prefix):
        for image in self.images:
            if image.get('alt', '').startswith(alt_prefix):
                prefix, encoded = image['src'].split(',', 1)
                if prefix != 'data:image/png;base64':
                    raise ValueError('A captura deve estar incorporada em PNG ao HTML.')
                return io.BytesIO(base64.b64decode(encoded, validate=True))
        raise ValueError(f'Captura não encontrada na apresentação: {alt_prefix}')


def screenshot(story, images, alt_prefix, caption, maxheight=12 * cm):
    image = Image(images.find(alt_prefix))
    ratio = min(WIDTH / image.imageWidth, maxheight / image.imageHeight)
    image.drawWidth = image.imageWidth * ratio
    image.drawHeight = image.imageHeight * ratio
    story.extend([image, p(caption, CAPTION)])


def load_evidence(name):
    file = QA / name
    if not file.is_file():
        raise FileNotFoundError(
            f'Falta {file.relative_to(ROOT)}. Execute make test, make sanitize e node tests/test_ui.cjs.'
        )
    data = json.loads(file.read_text())
    if not data.get('tests') or data['total'] != len(data['tests']):
        raise ValueError(f'Evidência incompleta: {file.relative_to(ROOT)}')
    return data


def execution_date(data):
    moment = datetime.datetime.fromisoformat(data['executed_at'].replace('Z', '+00:00'))
    return moment.astimezone(ZoneInfo('America/Belem')).strftime('%d/%m/%Y às %H:%M (UTC-3)')


def report():
    meta = json.loads((DOCS / 'equipe.json').read_text())
    names = meta['integrantes']
    if len(names) != len(set(names)) or any(name not in meta['matriculas'] for name in names):
        raise ValueError('Confira os nomes e as matrículas em docs/equipe.json.')
    if len({meta['matriculas'][name] for name in names}) != len(names):
        raise ValueError('Há matrículas repetidas em docs/equipe.json.')
    api = load_evidence('test-results.json')
    ui = load_evidence('ui-test-results.json')
    sanitized = load_evidence('sanitizer-test-results.json')
    images = PresentationImages()
    images.feed((DOCS / 'apresentacao.html').read_text())
    doc = AcademicDoc(
        str(DOCS / 'relatorio-tecnico.pdf'), pagesize=A4,
        leftMargin=3 * cm, rightMargin=2 * cm, topMargin=3 * cm, bottomMargin=2 * cm,
        title='Sistema de controle de vendas em C - Relatório técnico', author='; '.join(names),
    )
    frame = Frame(3 * cm, 2 * cm, WIDTH, A4[1] - 5 * cm, leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)
    doc.addPageTemplates(PageTemplate(id='academic', frames=[frame], onPage=academic_page))
    story = [p(plain(meta['instituicao']).upper(), COVER)]
    if not meta['curso'].startswith('[PREENCHER'):
        story.append(p(plain(meta['curso']), COVER))
    story.extend([p('Turma ' + plain(meta['turma']), COVER), Spacer(1, cm)])
    story.extend(p(plain(name).upper() + '<br/><font size=9>Matrícula: ' + plain(meta['matriculas'][name]) + '</font>', COVER) for name in names)
    story.extend([
        Spacer(1, 1.3 * cm), p('<b>SISTEMA DE CONTROLE DE VENDAS EM C</b>', COVER),
        p('Cadastro de produtos, registro de vendas e relatórios', COVER), Spacer(1, .8 * cm),
        p('Relatório técnico - ' + plain(meta['disciplina']) + '<br/>Professora: ' + plain(meta['professor']), COVER),
        Spacer(1, 1.2 * cm),
    ])
    if not meta['cidade'].startswith('[PREENCHER'):
        story.append(p(plain(meta['cidade']), COVER))
    story.extend([p(plain(meta['ano']), COVER), PageBreak(), p('<b>SUMÁRIO</b>', COVER), Spacer(1, .5 * cm)])
    toc = TableOfContents()
    toc.levelStyles = [
        ParagraphStyle('TOC0', fontName=FONT_BODY, fontSize=11, leading=16, spaceBefore=4),
        ParagraphStyle('TOC1', fontName=FONT_BODY, fontSize=10, leading=14, leftIndent=15),
    ]
    story.extend([toc, PageBreak()])

    heading(story, '1 INTRODUÇÃO')
    paragraphs(story,
        'Pequenos estabelecimentos precisam conhecer os produtos disponíveis, registrar cada venda e consultar os valores vendidos. A aplicação reúne essas informações em um sistema local, com interface gráfica no navegador e persistência em arquivo.',
        'O sistema apresenta três telas: Produtos, Vendas e Relatórios. O cadastro mantém nome, código, categoria, preço, estoque e situação dos produtos. Cada venda calcula o total, baixa as quantidades e fica disponível no histórico. O relatório informa a quantidade de vendas concluídas e o total vendido no período selecionado.',
        'O servidor, as validações e as regras de negócio usam C11. O frontend usa Angular e TypeScript, com HTML e CSS para a apresentação visual. O SQLite armazena os dados e o cJSON faz a leitura e a geração de JSON. Após instalar as dependências e compilar, o sistema funciona localmente.',
    )
    heading(story, '2 OBJETIVOS')
    heading(story, '2.1 Objetivo geral', 2)
    paragraphs(story, 'Organizar o cadastro de produtos e o registro de vendas de uma pequena loja, mantendo o estoque coerente e permitindo a consulta do total vendido com recuperação dos registros após reiniciar a aplicação.')
    heading(story, '2.2 Objetivos específicos', 2)
    paragraphs(story, 'Implementar cadastro, listagem, pesquisa, edição e exclusão de produtos; validar entradas e códigos repetidos; calcular valores em centavos; registrar vendas com baixa de estoque; consultar histórico e relatórios por período; aplicar funções, estruturas, ponteiros e memória dinâmica em C; e verificar os fluxos com testes de integração e de interface.')

    heading(story, '3 REQUISITOS DO SISTEMA', new_page=True)
    heading(story, '3.1 Funcionalidades e requisitos técnicos', 2)
    requirements = [
        ('R01', 'Menu, retorno e encerramento', 'Três telas, botões Voltar, Ctrl+C ou docker compose stop.'),
        ('R02', 'Struct com identificador e campos', 'Product, Sale e SaleItem em include/app.h.'),
        ('R03', 'Cadastrar, consultar, alterar e excluir', 'CRUD de produtos, código único e busca no catálogo.'),
        ('R04', 'Regras específicas', 'Cálculo monetário e baixa de estoque na mesma venda.'),
        ('R05', 'Condicionais e laços', 'Validações, processamento de itens e atendimento HTTP.'),
        ('R06', 'Funções e modularização', 'Nove arquivos C organizados por responsabilidade.'),
        ('R07', 'Ponteiros e memória dinâmica', 'calloc dos itens, buffers dinâmicos e liberação em sucesso e falha.'),
        ('R08', 'Persistência em arquivo', 'SQLite, transações e recuperação após reinício.'),
        ('R09', 'Validação de dados', 'Tipos, campos, limites, datas, pagamento, estoque e SKU repetido.'),
        ('R10', 'Arquivos .c e .h', 'Fontes próprios em src/ e contratos em include/.'),
    ]
    story.append(table(['Código', 'Requisito', 'Implementação'], requirements, [1.7 * cm, 4.8 * cm, WIDTH - 6.5 * cm]))
    heading(story, '3.2 Entradas, saídas e regras', 2)
    paragraphs(story,
        'O produto recebe código/SKU, nome, categoria, preço positivo, estoque inteiro e situação ativa ou inativa. A venda recebe os produtos e suas quantidades, cliente opcional e forma de pagamento. As opções são Pix, dinheiro, cartão de crédito e cartão de débito. O sistema registra a forma escolhida para controle interno.',
        'As saídas são o catálogo, o histórico com os detalhes das vendas, o comprovante interno e os totais por período. Novas vendas são registradas sem desconto. O relatório apresenta quantidade de vendas concluídas e total vendido, sem cálculo de lucro.',
        'O SKU é único, inclusive quando muda somente a caixa das letras ASCII. Produto inativo não pode ser vendido. A quantidade precisa ser inteira, positiva e menor ou igual ao saldo disponível. Produtos com vendas associadas não podem ser excluídos; podem ser desativados para preservar o histórico.',
        'Uma venda aceita de 1 a 200 produtos distintos. Estoques e quantidades têm limite de 1.000.000 de unidades. O preço unitário máximo é R$ 1.000.000,00 e o total máximo da venda é R$ 90.000.000.000,00. Campos de texto têm limites em bytes UTF-8. O total resulta da soma de quantidade multiplicada pelo preço atual de cada produto.',
    )

    heading(story, '4 DESENVOLVIMENTO', new_page=True)
    heading(story, '4.1 Arquitetura e tecnologias', 2)
    paragraphs(story,
        'O navegador apresenta os componentes Angular e envia requisições HTTP com JSON. O servidor em C recebe as requisições, aplica as regras e consulta ou altera o SQLite. A resposta atualiza a interface. O mesmo processo entrega a API e os arquivos gerados pelo build do Angular, evitando a necessidade de um servidor separado para o frontend.',
        'Por padrão, o endereço é http://127.0.0.1:8080. Na execução com Docker, o servidor usa --host 0.0.0.0 dentro do contêiner, e o Compose publica a porta em 127.0.0.1 no computador. O banco permanece em um volume persistente.',
    )
    story.append(table(['Tecnologia', 'Papel'], [
        ('C11 e sockets POSIX', 'Servidor HTTP, validações e regras de negócio.'),
        ('Angular e TypeScript', 'Rotas, componentes, formulários e serviço HTTP compartilhado.'),
        ('HTML e CSS', 'Estrutura e apresentação visual das telas.'),
        ('SQLite', 'Banco local com transações e restrições de integridade.'),
        ('cJSON', 'Conversão dos corpos JSON recebidos e das respostas.'),
        ('Make, Node.js e npm', 'Compilação do servidor e build do Angular.'),
        ('Docker Compose', 'Execução em contêiner e persistência por volume.'),
        ('Python e Playwright', 'Testes, evidências e ferramentas de documentação.'),
    ], [4.2 * cm, WIDTH - 4.2 * cm]))
    heading(story, '4.2 Organização dos módulos', 2, new_page=True)
    story.append(table(['Arquivo', 'Responsabilidade'], [
        ('src/main.c', 'Argumentos de execução, abertura do banco e inicialização.'),
        ('src/http.c', 'Sockets, leitura de requisições, entrega da interface e encerramento.'),
        ('src/api.c', 'Seleção das rotas e encaminhamento para cada funcionalidade.'),
        ('src/products.c', 'Cadastro, consulta, edição e exclusão de produtos.'),
        ('src/sales.c', 'Registro e consulta das vendas, cálculo e baixa de estoque.'),
        ('src/reports.c', 'Quantidade de vendas concluídas e total vendido por período.'),
        ('src/api_helpers.c', 'Conversão de consultas para JSON e filtros compartilhados.'),
        ('src/database.c', 'Abertura do SQLite, esquema e preparação das consultas.'),
        ('src/utils.c', 'Validações, parâmetros da URL e respostas JSON.'),
    ], [4.1 * cm, WIDTH - 4.1 * cm]))
    paragraphs(story, 'O cabeçalho include/app.h reúne estruturas, limites e contratos da infraestrutura. Os cabeçalhos products.h, sales.h, reports.h e api_helpers.h declaram as funções dos novos módulos. No frontend, web/src/pages organiza as telas, dialogs reúne os formulários e detalhes, e shared concentra modelos, formatação e acesso à API.')
    heading(story, '4.3 Estruturas de dados e persistência', 2, new_page=True)
    story.append(table(['Estrutura C', 'Campos da versão atual'], [
        ('Product', 'id, sku, name, category, price_cents, stock e active.'),
        ('SaleItem', 'product_id e quantity.'),
        ('Sale', 'id, customer, payment_method, total_cents e ponteiro items.'),
    ], [3 * cm, WIDTH - 3 * cm]))
    paragraphs(story,
        'Product reúne os dados do catálogo. SaleItem representa o produto e a quantidade recebidos para uma venda. Sale mantém os dados da operação enquanto ela é validada e gravada. App mantém a conexão SQLite e o diretório da interface. Request e Response transportam os dados entre HTTP e API.',
        'No banco, products, sales e sale_items mantêm os registros persistentes. Os itens vendidos copiam código, nome e preço unitário do catálogo. Por isso, editar um produto depois não altera a descrição nem o preço das vendas anteriores. Chaves estrangeiras, SKU único e restrições CHECK também protegem a integridade.',
        'As estruturas C não repetem todas as colunas do banco. O esquema conserva campos antigos para ler arquivos já existentes, inclusive descontos e cancelamentos históricos. A versão atual não oferece novos descontos nem uma ação de cancelamento. Somente vendas com status completed entram nos totais do relatório.',
        'Datas são gravadas em UTC. A exibição e os filtros por dia usam o horário de Belém, UTC-3. Na execução local, o arquivo padrão é data/vendas.db. O mesmo arquivo pode ser indicado novamente com --db para recuperar os registros.',
    )
    heading(story, '4.4 Memória dinâmica e transações', 2)
    paragraphs(story, 'create_sale, em src/sales.c, conhece a quantidade de itens somente durante a requisição. A função usa calloc para reservar um vetor de SaleItem, verifica o resultado e libera o vetor tanto na conclusão quanto nos caminhos de erro. O servidor também usa buffers dinâmicos para processar as requisições.')
    story.append(Preformatted(
        'sale.items = calloc((size_t)count, sizeof(*sale.items));\n'
        'if (!sale.items)\n'
        '    return error_response(500, "Memoria insuficiente...");\n'
        '/* O vetor e liberado ao concluir ou desfazer a operacao. */\n'
        'free(sale.items);', CODE,
    ))
    paragraphs(story,
        'A venda inicia BEGIN IMMEDIATE antes de ler preços e estoques. Depois valida os produtos, calcula o total, insere a venda e os itens e atualiza os saldos. COMMIT confirma o conjunto. Uma falha aciona ROLLBACK, evitando venda parcial ou alteração isolada do estoque.',
        'Os preços recebidos do navegador não definem o valor final. O servidor lê os preços do banco e usa inteiros de 64 bits em centavos. Por exemplo, três unidades de R$ 0,10 resultam em 30 centavos, equivalentes a R$ 0,30.',
    )
    heading(story, '4.5 Fluxo e funções principais', 2)
    story.extend([flowchart(), p('Figura 1 - Fluxo geral da aplicação. Fonte: elaboração com base no código.', CAPTION)])
    paragraphs(story, 'db_open prepara a conexão e o esquema. http_run mantém o atendimento e api_route escolhe a operação. save_product e delete_product mantêm o catálogo; create_sale registra a venda; get_sales e get_sale recuperam o histórico; e get_report agrega os totais. http_stop sinaliza o encerramento do servidor.')

    heading(story, '5 TESTES E RESULTADOS', new_page=True)
    paragraphs(story, 'Os resultados desta seção vêm dos arquivos gerados pela versão atual em artifacts/qa/. Os testes usam bancos separados em tests/.runtime e não alteram o banco de trabalho da loja. Cada evidência informa o comando, o momento da execução e os casos verificados.')
    heading(story, '5.1 Integração da API e do banco', 2)
    cases = [(test['test'].split('_', 2)[1], test['description'], test['result']) for test in api['tests']]
    story.append(table(['Caso', 'Verificação executada', 'Resultado'], cases, [1.5 * cm, WIDTH - 4 * cm, 2.5 * cm]))
    paragraphs(story,
        f'Resultado: {api["total"]} testes, {api["failures"]} falhas e {api["errors"]} erros. Execução em {execution_date(api)}. Comando: make test. Evidência: artifacts/qa/test-results.json.',
        'Entre as verificações estão a soma exata do total, a redução do estoque, a preservação dos dados históricos e o rollback quando um dos produtos não possui saldo. A recuperação após reinício compara os registros antes e depois de reabrir o servidor e executa PRAGMA integrity_check e PRAGMA foreign_key_check.',
    )
    heading(story, '5.2 Interface e memória', 2)
    story.append(table(['Fluxo no Chrome', 'Resultado'], [(test['test'], test['result']) for test in ui['tests']], [WIDTH - 2.5 * cm, 2.5 * cm]))
    paragraphs(story,
        f'A execução da interface registrou {ui["total"]} fluxos em {execution_date(ui)}. Comando: node tests/test_ui.cjs. Evidência: artifacts/qa/ui-test-results.json. Os fluxos incluem as três telas, formulários, detalhes da venda, filtro do relatório, layout no celular e verificação de erros JavaScript e da política de conteúdo.',
        f'Com AddressSanitizer e UndefinedBehaviorSanitizer, a execução registrou {sanitized["total"]} testes, {sanitized["failures"]} falhas e {sanitized["errors"]} erros em {execution_date(sanitized)}. Comando: make sanitize. Evidência: artifacts/qa/sanitizer-test-results.json.',
        'Os sanitizadores instrumentam os módulos próprios em C, com detecção de vazamentos habilitada. SQLite e cJSON são ligados sem essa instrumentação. Os resultados descrevem os fluxos executados e não substituem testes de outras entradas e condições.',
    )
    heading(story, '5.3 Telas da aplicação atual', 2, new_page=True)
    paragraphs(story, 'As capturas a seguir mostram a interface atual com dados fictícios. São as imagens incorporadas à apresentação HTML, usadas aqui para ilustrar o cadastro, o registro de uma venda e a consulta por período.')
    screenshot(story, images, 'Formulário de edição', 'Figura 2 - Produto com código, categoria, nome, preço, estoque e situação.', 12 * cm)
    paragraphs(story, 'No exemplo, Café especial 250 g custa R$ 24,90 e possui 12 unidades em estoque. O registro de duas unidades resulta em R$ 49,80 e deixa saldo de 10 unidades. O relatório do dia selecionado apresenta uma venda e o mesmo total.')
    story.append(PageBreak())
    screenshot(story, images, 'Tela Nova venda', 'Figura 3 - Registro de duas unidades e total de R$ 49,80.', 10 * cm)
    story.append(Spacer(1, .6 * cm))
    screenshot(story, images, 'Relatório de', 'Figura 4 - Quantidade de vendas concluídas e total vendido no período.', 7 * cm)
    story.append(p('Fonte das figuras 2 a 4: capturas da aplicação incorporadas em docs/apresentacao.html. Dados fictícios de demonstração.', CAPTION))

    heading(story, '6 MANUAL DE UTILIZAÇÃO', new_page=True)
    heading(story, '6.1 Compilar e executar', 2)
    paragraphs(story,
        'Para compilar localmente, o projeto usa Linux ou WSL, compilador C11, GNU Make e Node.js 24 LTS (24.15 ou superior) com npm. SQLite e cJSON acompanham os fontes em vendor/. O comando make compila o servidor e gera a interface Angular em web/dist/browser. O navegador acessa os arquivos e a API pelo mesmo endereço.',
        'O script iniciar.sh entra na pasta do projeto, executa make e inicia o servidor. Por padrão, ele cria ou abre data/vendas.db e atende em http://127.0.0.1:8080. Ctrl+C encerra o processo. Fechar somente a aba do navegador mantém o servidor em execução.',
    )
    story.append(Preformatted(
        './iniciar.sh\n\n'
        '# Alternativa manual:\nmake\n./build/vendas\n\n'
        '# Usar uma copia do banco ficticio:\n'
        'cp data/exemplo.db data/demonstracao.db\n'
        './build/vendas --db data/demonstracao.db --port 8081\n\n'
        '# Alternativa com Docker:\n'
        'docker compose up --build -d --wait\n'
        'docker compose stop', CODE,
    ))
    paragraphs(story, 'O banco de exemplo contém oito produtos e seis vendas fictícias, inclusive dados históricos de versões anteriores. A cópia permite experimentar sem modificar o arquivo original. O servidor aceita --db, --host, --port, --web e --help. A porta deve estar entre 1024 e 65535.')
    heading(story, '6.2 Operação diária', 2)
    paragraphs(story,
        '<b>Produtos:</b> selecionar Novo produto, preencher código, nome, categoria, preço e estoque e confirmar. A busca encontra nome, código ou categoria. Os botões de edição e exclusão permitem manter o catálogo. Se o produto já tiver vendas, a exclusão é recusada e ele pode ser desativado.',
        '<b>Vendas:</b> selecionar Nova venda, buscar os produtos, ajustar as quantidades e escolher o pagamento. O cliente é opcional. Finalizar venda aciona o cálculo definitivo no servidor, a gravação dos itens e a baixa do estoque. Produtos inativos ou sem saldo suficiente são recusados.',
        '<b>Histórico:</b> usar a tela Vendas para pesquisar cliente ou número e aplicar um intervalo de datas. O botão de visualização abre os itens, valores e pagamento. O comprovante é de controle interno e não é um documento fiscal.',
        '<b>Relatórios:</b> informar as datas inicial e final e selecionar Aplicar. A tela apresenta a quantidade de vendas concluídas e o total vendido no período, considerando os dias no horário de Belém.',
    )
    heading(story, '6.3 Testes, documentos e cópia de segurança', 2)
    story.append(Preformatted(
        'make test\nmake sanitize\n\n'
        '# Ferramentas de navegador e documentacao:\n'
        'python3 scripts/setup-tools.py\n'
        'node tests/test_ui.cjs\n'
        'PYTHONPATH=.tools/python python3 scripts/generate_docs.py --report-only\n'
        'node scripts/export_presentation.cjs\n\n'
        '# Pacote de entrega:\nmake package', CODE,
    ))
    paragraphs(story,
        'O gerador do relatório lê os três resultados atuais de artifacts/qa/ e as capturas incorporadas ao HTML. Execute os testes antes de gerar o documento. A opção --report-only atualiza somente o relatório técnico. A exportação da apresentação atualiza o PDF e o roteiro a partir do HTML.',
        'Para uma cópia de segurança manual, encerre o servidor antes de copiar o banco, permitindo que o SQLite finalize o uso do WAL. Guarde o arquivo em outro local e restaure com o servidor encerrado. Com Docker, os dados ficam no volume vendas_dados. make clean remove objetos, executável e web/dist, preservando os bancos.',
    )

    heading(story, '7 CONCLUSÃO', new_page=True)
    paragraphs(story,
        'A aplicação integra o cadastro de produtos, o registro de vendas e a consulta do total vendido. O servidor em C mantém os cálculos e as validações, enquanto Angular apresenta a interface e SQLite preserva os registros. As transações ligam a gravação da venda à atualização dos saldos.',
        'A divisão em nove módulos C separa inicialização, HTTP, rotas, produtos, vendas, relatórios, auxiliares, banco e validações. Os testes documentados verificam os fluxos atuais, o tratamento de entradas inválidas e a recuperação dos dados após reiniciar.',
        'O escopo é um controle interno local, com atendimento sequencial. Autenticação, emissão fiscal, operação remota multiusuário e cálculo de lucro podem ser considerados em trabalhos futuros. A equipe deve compreender a implementação e revisar a adequação do documento ao modelo institucional solicitado.',
    )
    heading(story, '8 REFERÊNCIAS', new_page=True)
    references = [
        'PROJETO PRÁTICO - DESENVOLVIMENTO DE SOFTWARE EM C. Enunciado da disciplina Programação de Software Básico em C, 2026. Arquivo fornecido: Projeto_Pratico_C_4_Pontos.pdf.',
        'CONTROLE DE VENDAS. Código-fonte da aplicação: src/, include/, web/src/, Makefile e compose.yaml. Instruções de execução em README.md e README.txt.',
        'CONTROLE DE VENDAS. Resultados da versão atual: artifacts/qa/test-results.json, artifacts/qa/ui-test-results.json e artifacts/qa/sanitizer-test-results.json. Capturas ilustrativas em docs/apresentacao.html.',
        'SQLITE. Código-fonte e interface C incorporados em vendor/sqlite. Identificação e declaração de domínio público nos arquivos da biblioteca.',
        'GAMBLE, Dave et al. cJSON. Código-fonte e licença MIT incorporados em vendor/cjson.',
        'ANGULAR. Framework e ferramentas de build declarados em web/package.json. Interface da aplicação em web/src/.',
        'MICROSOFT. Playwright. Automação dos fluxos de navegador em tests/test_ui.cjs e exportação da apresentação em scripts/export_presentation.cjs.',
        'REPORTLAB. ReportLab Toolkit. Geração do relatório em scripts/generate_docs.py.',
        'OPENAI. Codex. Assistência na elaboração e revisão do código, dos testes e dos documentos. A equipe é responsável por revisar, adaptar e compreender os materiais.',
    ]
    reference_style = ParagraphStyle('Reference', parent=BODY, alignment=TA_LEFT, firstLineIndent=0, leading=15, spaceAfter=13)
    story.extend(p(plain(reference), reference_style) for reference in references)
    heading(story, '9 APÊNDICE - APRESENTAÇÃO DA APLICAÇÃO', new_page=True)
    paragraphs(story, 'A apresentação atual tem 11 slides e concentra a exposição no propósito da aplicação, no uso das telas e nas tecnologias. O HTML oferece navegação por teclado, tela cheia e notas para a fala. O PDF apresenta o mesmo conteúdo com um slide por página. A duração sugerida é de aproximadamente 12 minutos, com espaço adicional para demonstração e perguntas.')
    story.append(table(['Responsável', 'Assuntos'], [
        (names[0], 'Apresentação da aplicação e propósito.'),
        (names[1], 'Fluxo de uso e cadastro de produtos.'),
        (names[2], 'Registro e exemplo de uma venda.'),
        (names[3], 'Histórico e relatório por período.'),
        (names[4], 'Funcionamento interno e tecnologias.'),
        (names[5], 'Encerramento e perguntas.'),
    ], [7.2 * cm, WIDTH - 7.2 * cm]))
    paragraphs(story,
        'O exemplo da apresentação acompanha duas unidades de café a R$ 24,90. O total é R$ 49,80 e o estoque passa de 12 para 10 unidades. A consulta do dia demonstra como a mesma venda aparece no histórico e no relatório.',
        'Materiais: docs/apresentacao.html, docs/apresentacao.pdf e docs/roteiro-apresentacao.txt. A distribuição organiza a fala e não comprova contribuições individuais no desenvolvimento. Todos os integrantes devem conhecer a solução e responder às perguntas sobre ela.',
    )
    doc.multiBuild(story)
    print('Relatório técnico atualizado: docs/relatorio-tecnico.pdf')


def slides(pdf_only=False):
    """O argumento antigo permanece aceito; a fonte dos slides agora é o HTML."""
    subprocess.run(['node', str(ROOT / 'scripts' / 'export_presentation.cjs')], cwd=ROOT, check=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--report-only', action='store_true', help='Gera somente o relatório técnico.')
    parser.add_argument('--pdf-only', action='store_true', help=argparse.SUPPRESS)
    args = parser.parse_args()
    report()
    if not args.report_only:
        slides(pdf_only=args.pdf_only)
        from generate_sales_pdf import sales_report
        sales_report()
