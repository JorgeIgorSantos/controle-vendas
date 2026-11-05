#!/usr/bin/env python3
"""Gera os documentos acadêmicos a partir da identificação e de resultados reais."""
from pathlib import Path
import datetime
import json
from xml.sax.saxutils import escape

from reportlab import rl_config
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm, inch
from reportlab.pdfgen import canvas
from reportlab.platypus import (BaseDocTemplate, Frame, PageTemplate, Paragraph, Spacer,
                              PageBreak, Table, TableStyle, Image, KeepTogether, Preformatted)
from reportlab.platypus.tableofcontents import TableOfContents
from reportlab.graphics.shapes import Drawing, Rect, String, Line, Polygon
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE

ROOT=Path(__file__).resolve().parents[1]
DOCS=ROOT/'docs'
ART=ROOT/'artifacts'
META=json.loads((DOCS/'equipe.json').read_text())
API=json.loads((ART/'test-results.json').read_text())
UI=json.loads((ART/'ui-test-results.json').read_text())
SAN=json.loads((ART/'sanitizer-test-results.json').read_text())
assert len(META['integrantes']) == len(set(META['integrantes'])), 'Integrante duplicado'
assert len(set(META['matriculas'].values())) == len(META['integrantes']), 'Matrícula duplicada'
assert all(name in META['matriculas'] for name in META['integrantes'])
assert API['total']==18 and not API['failures'] and not API['errors']
assert UI['total']==9 and all(t['result']=='APROVADO' for t in UI['tests'])
assert SAN['total']==18 and not SAN['failures'] and not SAN['errors']
ORANGE=colors.HexColor('#ed663f')
INK=colors.HexColor('#25303b')
GRAY=colors.HexColor('#77808d')
LIGHT=colors.HexColor('#f6f7f9')
WIDTH=A4[0]-5*cm
STYLES=getSampleStyleSheet()
BODY=ParagraphStyle('AcademicBody',fontName='Times-Roman',fontSize=12,leading=18,alignment=TA_JUSTIFY,spaceAfter=9,firstLineIndent=1.25*cm)
H1=ParagraphStyle('AcademicHeading',fontName='Times-Bold',fontSize=12,leading=18,spaceBefore=15,spaceAfter=12,keepWithNext=True)
H2=ParagraphStyle('AcademicSubheading',parent=H1,fontSize=12,spaceBefore=12,spaceAfter=8,keepWithNext=False)
CAPTION=ParagraphStyle('AcademicCaption',fontName='Times-Roman',fontSize=10,leading=13,alignment=TA_CENTER,spaceBefore=6,spaceAfter=10)
CELL=ParagraphStyle('TableCell',fontName='Times-Roman',fontSize=9,leading=12,spaceAfter=0)
HEADER=ParagraphStyle('TableHeader',parent=CELL,fontName='Times-Bold',textColor=colors.white)
COVER=ParagraphStyle('Cover',fontName='Times-Roman',fontSize=12,leading=19,alignment=TA_CENTER)
CODE=ParagraphStyle('Code',fontName='Courier',fontSize=8.2,leading=11,backColor=LIGHT,borderPadding=8,spaceBefore=8,spaceAfter=12)

def p(text,style=BODY):return Paragraph(text,style)
def plain(text):return escape(str(text)).replace('\n','<br/>')
def student(name):
    return plain(name).upper()+'<br/><font size=9>Matrícula: '+plain(META['matriculas'][name])+'</font>'

def table(headers,rows,widths=None):
    data=[[p(plain(h),HEADER) for h in headers]]+[[p(plain(v),CELL) for v in row] for row in rows]
    tab=Table(data,colWidths=widths or [WIDTH/len(headers)]*len(headers),repeatRows=1,hAlign='LEFT')
    tab.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),INK),('VALIGN',(0,0),(-1,-1),'TOP'),('TOPPADDING',(0,0),(-1,-1),5),('BOTTOMPADDING',(0,0),(-1,-1),5),('LEFTPADDING',(0,0),(-1,-1),7),('RIGHTPADDING',(0,0),(-1,-1),7),('ROWBACKGROUNDS',(0,1),(-1,-1),[colors.white,LIGHT]),('LINEBELOW',(0,0),(-1,0),.5,INK),('LINEBELOW',(0,1),(-1,-1),.25,colors.HexColor('#e5e7eb'))]))
    return tab

class AcademicDoc(BaseDocTemplate):
    def afterFlowable(self,flowable):
        if isinstance(flowable,Paragraph) and flowable.style.name in {'AcademicHeading','AcademicSubheading'}:
            level=0 if flowable.style.name=='AcademicHeading' else 1
            key=f'heading-{self.seq.nextf("section")}'
            self.canv.bookmarkPage(key)
            self.canv.addOutlineEntry(flowable.getPlainText(),key,level=level,closed=False)
            self.notify('TOCEntry',(level,flowable.getPlainText(),self.page-1,key))

def academic_page(c,doc):
    if doc.page>=3:
        c.saveState();c.setFont('Times-Roman',10);c.drawRightString(A4[0]-2*cm,A4[1]-2*cm,str(doc.page-1));c.restoreState()

def flowchart():
    d=Drawing(WIDTH,260)
    labels=[('Iniciar executável C',280),('Abrir ou criar arquivo SQLite',228),('Interface gráfica e menu',176),('Produtos | Vendas | Relatórios',124),('Validar, processar e persistir',72),('Retornar ao menu ou encerrar',20)]
    x=(WIDTH-300)/2
    for i,(label,y) in enumerate(labels):
        d.add(Rect(x,y,300,36,rx=7,ry=7,fillColor=colors.HexColor('#fff4ed') if i in (0,5) else LIGHT,strokeColor=colors.HexColor('#e3e6eb'),strokeWidth=.7))
        d.add(String(WIDTH/2,y+14,label,fontName='Times-Roman',fontSize=11,textAnchor='middle',fillColor=INK))
        if i<len(labels)-1:
            d.add(Line(WIDTH/2,y,WIDTH/2,y-12,strokeColor=GRAY,strokeWidth=1))
            d.add(Polygon([WIDTH/2-3,y-10,WIDTH/2,y-16,WIDTH/2+3,y-10],fillColor=GRAY,strokeColor=GRAY))
    d.scale(.75,.75)
    d.width=WIDTH*.75
    d.hAlign='CENTER'
    return d

def screenshot(story,name,caption,maxheight=18*cm):
    item=Image(str(ART/name));ratio=min(WIDTH/item.imageWidth,maxheight/item.imageHeight);item.drawWidth=item.imageWidth*ratio;item.drawHeight=item.imageHeight*ratio
    story.extend([item,p(caption,CAPTION),p('Fonte: captura da aplicação. As evidências de testes estão em artifacts/.',CAPTION)])

def report():
    doc=AcademicDoc(str(DOCS/'relatorio-tecnico.pdf'),pagesize=A4,leftMargin=3*cm,rightMargin=2*cm,topMargin=3*cm,bottomMargin=2*cm,title='Sistema de controle de vendas em C — Relatório técnico',author='; '.join(META['integrantes']))
    doc.addPageTemplates(PageTemplate(id='academic',frames=[Frame(3*cm,2*cm,WIDTH,A4[1]-5*cm,leftPadding=0,rightPadding=0,topPadding=0,bottomPadding=0)],onPage=academic_page))
    story=[]
    story += [p(plain(META['instituicao']).upper(),COVER)]
    if not META['curso'].startswith('[PREENCHER'):
        story += [p(plain(META['curso']),COVER)]
    story += [p('Turma '+plain(META['turma']),COVER),Spacer(1,1*cm)]
    story += [p(student(n),COVER) for n in META['integrantes']]
    story += [Spacer(1,1.3*cm),p('<b>SISTEMA DE CONTROLE DE VENDAS EM C</b>',COVER),
              p('Cadastro de produtos, registro de vendas e relatórios',COVER),Spacer(1,.8*cm)]
    submission=ParagraphStyle('Submission',parent=COVER,fontSize=10,leading=14)
    story += [p('Relatório técnico - '+plain(META['disciplina'])+'<br/>Professora: '+plain(META['professor']),submission),Spacer(1,1.5*cm)]
    if not META['cidade'].startswith('[PREENCHER'):
        story += [p(plain(META['cidade']),COVER)]
    story += [p(plain(META['ano']),COVER),PageBreak()]
    story += [p('<b>SUMÁRIO</b>',COVER),Spacer(1,.5*cm)]
    toc=TableOfContents();toc.levelStyles=[ParagraphStyle('TOC0',fontName='Times-Roman',fontSize=11,leading=16,leftIndent=0,firstLineIndent=0,spaceBefore=4),ParagraphStyle('TOC1',fontName='Times-Roman',fontSize=10,leading=14,leftIndent=15,firstLineIndent=0)]
    story += [toc,PageBreak(),p('1 INTRODUÇÃO',H1)]
    story += [p('Pequenos estabelecimentos precisam registrar produtos e vendas de maneira consistente. Anotações dispersas dificultam o acompanhamento do estoque, aumentam o risco de erros de cálculo e tornam a apuração dos resultados mais trabalhosa. O problema escolhido consiste em reunir essas informações em uma aplicação local, com interface gráfica e recuperação dos dados após o encerramento do programa.'),p('O sistema Venda. permite cadastrar produtos e seus preços, registrar vendas, calcular automaticamente o total de cada operação e gerar relatórios do total vendido. A proposta também inclui estoque mínimo, descontos, formas de pagamento e cancelamento com devolução dos produtos, para demonstrar regras relacionadas ao tema.'),p('O desenvolvimento segue os requisitos do documento Projeto Prático — Desenvolvimento de Software em C, fornecido com a atividade. O núcleo da solução é escrito em C11, dividido em arquivos .c e .h. A interface gráfica é apresentada no navegador; o servidor HTTP, as validações, os cálculos, as transações e o acesso ao SQLite são executados em C.'),p('O público considerado é o responsável por uma pequena loja, em uso local, além dos integrantes da equipe durante a demonstração acadêmica. Não é necessário acesso à internet para executar o sistema depois de obter os arquivos do projeto.'),p('2 OBJETIVOS',H1),p('2.1 Objetivo geral',H2),p('Desenvolver uma aplicação em C com interface gráfica e persistência em arquivo para organizar produtos, registrar vendas e apresentar o total vendido com integridade de estoque e precisão monetária.'),p('2.2 Objetivos específicos',H2),p('Implementar cadastro, listagem, pesquisa, atualização e exclusão de produtos; validar identificadores e entradas; aplicar regras de estoque e desconto; preservar o histórico de cada venda; demonstrar estruturas, ponteiros e memória dinâmica; recuperar informações após reiniciar; executar testes com dados válidos e inválidos; e documentar a compilação e o uso.'),PageBreak(),p('3 REQUISITOS DO SISTEMA',H1)]
    reqs=[('R01','Interface gráfica com menu, retorno e encerramento','Quatro seções, modais, Ctrl+C e docker compose stop.'),('R02','Struct com identificador e cinco campos relevantes','Product, Sale e SaleItem em include/app.h.'),('R03','Cadastrar, listar, pesquisar, atualizar e excluir','CRUD de produtos e filtros no catálogo.'),('R04','Regras específicas do tema','Venda, baixa de estoque, cálculo, cancelamento e relatório.'),('R05','Condicionais e repetição','Validações, laços de itens e laço do servidor.'),('R06','Funções e modularização','main, http, api, database e utils.'),('R07','Ponteiros e memória dinâmica','calloc de itens e malloc/calloc de buffers; verificação e free.'),('R08','Persistência em arquivos','Arquivo SQLite, transações e reabertura.'),('R09','Validação de entradas','Campos vazios, tipos, limites, estoque, datas e SKU único.'),('R10','Arquivos .c e .h organizados','Fontes próprios separados de bibliotecas incorporadas.')]
    story += [p('3.1 Funcionalidades e requisitos técnicos',H2),table(['Código','Requisito do PDF','Atendimento'],reqs,[1.3*cm,6.4*cm,WIDTH-7.7*cm]),Spacer(1,.3*cm),p('3.2 Entradas, saídas e regras',H2),p('As entradas são código/SKU, nome, categoria, preço, estoque, estoque mínimo, situação e observações dos produtos. Na venda, o usuário informa os produtos, as quantidades, o cliente opcional, a forma de pagamento, o desconto e observações. As saídas incluem catálogo, histórico, detalhes, comprovante interno, indicadores, gráfico diário e exportação CSV.'),p('O preço unitário deve ser positivo. Quantidades são inteiras; estoque negativo e venda acima do saldo são proibidos. O desconto não pode superar o subtotal. O código/SKU é único, com comparação sem distinção de maiúsculas ASCII. O identificador interno é gerado pelo SQLite. Produtos com histórico são desativados, em vez de excluídos, para preservar as referências.'),p('O total de uma venda é a soma de quantidade × preço unitário menos o desconto. Todos os cálculos monetários do backend usam inteiros de 64 bits em centavos. Uma venda pode ter até 200 produtos distintos, preço unitário de até R$ 1.000.000,00 e subtotal de até R$ 90.000.000.000,00. Estoques são limitados a 1.000.000 de unidades. Campos de texto têm limites em bytes UTF-8.'),PageBreak(),p('4 DESENVOLVIMENTO',H1),p('4.1 Arquitetura e decisões',H2),p('O servidor foi implementado em C com sockets POSIX e atende somente o endereço local 127.0.0.1. Ele entrega tanto os arquivos da interface quanto os endpoints JSON, mantendo uma única origem de acesso. O navegador usa HTML, CSS e JavaScript sem framework. O JavaScript apresenta os dados e calcula apenas uma prévia do carrinho; os valores definitivos são recalculados em C, a partir dos preços do banco.'),p('O SQLite foi escolhido por armazenar o banco em um arquivo e oferecer transações e chaves estrangeiras sem exigir um servidor de banco separado. A biblioteca cJSON converte os corpos JSON recebidos e as respostas. Os códigos dessas duas bibliotecas estão incluídos em vendor, com identificação e licença. Os arquivos da aplicação são compilados com -Wall, -Wextra, -Wpedantic e -Werror.'),table(['Módulo','Responsabilidade'],[('main.c','Parâmetros, abertura do banco e inicialização.'),('http.c','Sockets, limites de requisição, arquivos gráficos e encerramento.'),('api.c','CRUD, validação, venda, cancelamento, consultas e relatórios.'),('database.c','Esquema, abertura, transações e dados opcionais de exemplo.'),('utils.c','Conversões, validação de texto/número/data e respostas JSON.'),('app.h','Structs, constantes e contratos entre módulos.')],[3.5*cm,WIDTH-3.5*cm]),p('4.2 Estruturas de dados e persistência',H2),table(['Estrutura','Campos principais'],[('Product','id, sku, name, category, price_cents, stock, min_stock, active, notes.'),('Sale','id, customer, payment_method, subtotal_cents, discount_cents, total_cents, notes, items, item_count.'),('SaleItem','product_id, sku, name, quantity, unit_price_cents e total_cents.')],[3*cm,WIDTH-3*cm]),p('As tabelas products, sales e sale_items representam os registros persistentes. Uma venda possui vários itens, e cada item referencia o produto original. O nome, o código e o preço unitário são copiados para o item da venda. Assim, editar o catálogo não modifica o histórico. O banco usa restrições CHECK, código único e chaves estrangeiras.'),p('4.3 Ponteiros, alocação e transações',H2),p('A quantidade de itens de uma venda só é conhecida em execução. A função create_sale aloca um vetor de SaleItem com calloc, verifica o retorno e libera o vetor com free tanto no sucesso quanto nos caminhos de falha. Ponteiros também são usados nas estruturas de requisição, conexão SQLite, comandos preparados e buffers de comunicação.'),Preformatted('sale.items = calloc(sale.item_count, sizeof(*sale.items));\nif (!sale.items)\n    return error_response(500, "Memória insuficiente...");\n/* O vetor é liberado ao concluir ou desfazer a operação. */\nfree(sale.items);',CODE),p('Antes de ler e gravar os itens, a venda inicia BEGIN IMMEDIATE. O programa valida o estoque atual, calcula os valores, insere a venda e seus itens e atualiza os estoques. COMMIT confirma o conjunto. Qualquer falha leva a ROLLBACK, evitando venda parcial. O cancelamento também é transacional e só devolve estoque uma vez. O preço informado pelo cliente não é usado como fonte do valor definitivo.'),p('4.4 Fluxograma geral',H2),flowchart(),p('Figura 1 — Fluxo geral do sistema. Fonte: elaboração para este projeto.',CAPTION),p('4.5 Funções principais',H2),p('db_open prepara o arquivo e o esquema. api_route seleciona a operação. save_product valida e persiste o produto; get_products permite pesquisa; delete_product protege o histórico. create_sale calcula e grava a venda; cancel_sale faz a reposição; get_report agrega os resultados. http_run mantém o ciclo de atendimento e http_stop encerra o servidor após responder à interface.'),PageBreak(),p('5 TESTES E RESULTADOS',H1),p('Os testes foram executados contra o binário C real, por HTTP, utilizando arquivos SQLite isolados em tests/.runtime. A recuperação foi comprovada pelo encerramento e pela inicialização de outro processo com o mesmo arquivo. A integridade foi verificada com PRAGMA integrity_check e PRAGMA foreign_key_check. Os resultados abaixo foram extraídos dos registros JSON da execução, e não apenas previstos.'),p('5.1 Testes da API e do banco',H2)]
    actions=[('Banco vazio','Consultar listas e relatório sem registros','Listas vazias e total zero'),('CRUD','Criar, buscar, alterar e excluir produto','Dados atualizados; exclusão confirmada'),('Duplicidade','Repetir código no cadastro/edição','HTTP 409; código único'),('Produto inválido','Vazio, preço zero e estoque inválido','HTTP 400; nenhuma gravação'),('Venda e histórico','2 × 24,90 + 39,90 − 9,70','Total 80,00; estoque reduzido; histórico fixo'),('Atomicidade','Segundo item sem estoque','HTTP 409; nenhum saldo alterado'),('Venda inválida','Vazia, repetida, inativa ou desconto alto','Recusar operação inválida'),('Cancelamento','Cancelar e tentar cancelar novamente','Reposição única; total ajustado'),('Relatórios','Somar vendas e filtrar datas','Somas exatas; datas inválidas recusadas'),('Inexistentes','Consultar ID ausente e rota inválida','HTTP 404/405; arquivos protegidos'),('Reinício','Encerrar e reabrir o mesmo banco','Recuperar produtos, vendas e totais'),('HTTP/JSON','Origem externa e corpo inválido','Recusar com 403/400/415'),('Centavos','3 × 0,10 − 0,01','Total exato de 0,29'),('Restrições SQL','Tentar estoque negativo e SKU repetido','SQLite rejeita alterações'),('Interface estática','Solicitar HTML, JS, CSS e SVG','HTTP 200 e tipos corretos'),('Limite de reposição','Cancelamento ultrapassaria estoque máximo','Recusar sem alterar a venda'),('Exemplos','Iniciar duas vezes com --demo','8 produtos e 6 vendas, sem duplicar'),('Encerramento','Acionar /api/shutdown e reiniciar','Saída normal e dados preservados')]
    rows=[]
    for i,(name,action,expected) in enumerate(actions):rows.append((f'{i+1:02d} — {name}',action,expected,API['tests'][i]['result']))
    story += [table(['Teste','Entrada ou ação','Resultado esperado','Obtido'],rows,[3.2*cm,4.3*cm,5.3*cm,WIDTH-12.8*cm]),Spacer(1,.3*cm),p(f'Resultado registrado: {API["total"]} testes aprovados, {API["failures"]} falhas e {API["errors"]} erros. Execução: {plain(API["executed_at"])}. Arquivo: artifacts/test-results.json.'),p('5.2 Interface e memória',H2),table(['Fluxo no Chrome','Resultado obtido'],[(r['test'],r['result']) for r in UI['tests']],[WIDTH-3*cm,3*cm]),p('Os mesmos 18 testes da API também passaram com AddressSanitizer e UndefinedBehaviorSanitizer, com detecção de vazamentos habilitada nos módulos próprios da aplicação. As bibliotecas incorporadas SQLite e cJSON foram ligadas sem instrumentação. Isso verifica o conjunto de fluxos executados e não equivale a provar ausência de qualquer falha em entradas possíveis. Evidência: artifacts/sanitizer-test-results.json.'),PageBreak(),p('5.3 Evidências da interface',H2)]
    screenshot(story,'interface-simplificada.png','Figura 2 — Visão geral com valores consultados no banco de demonstração.',16*cm)
    story += [PageBreak()]
    screenshot(story,'03-nova-venda.png','Figura 3 — Registro de venda com produtos, quantidades e desconto.',15*cm)
    screenshot(story,'05-validacao.png','Figura 4 — Mensagem de código de produto duplicado.',9*cm)
    story += [PageBreak(),p('6 MANUAL DE UTILIZAÇÃO',H1),p('6.1 Compilar e executar',H2),p('O projeto requer Linux ou WSL, compilador C11 (GCC/Clang), GNU Make e navegador atual. O SQLite e o cJSON já acompanham os fontes. Node e Python não são exigidos para usar o sistema; Python 3 é necessário apenas para os testes e as ferramentas de entrega.'),Preformatted('./iniciar.sh\n# Abrir http://127.0.0.1:8080\n\n# Alternativa manual:\nmake\n./build/vendas\n\n# Exemplos opcionais em um banco vazio:\n./iniciar.sh --demo\n\n# Outra porta e outro arquivo:\n./build/vendas --port 8081 --db data/minha-loja.db',CODE),p('O script iniciar.sh muda para a pasta do projeto antes de compilar. O banco padrão é data/vendas.db e é criado automaticamente. O servidor pode ser encerrado por Ctrl+C no terminal ou por docker compose stop quando executado em contêiner. Fechar apenas o navegador mantém o programa em execução. Ao iniciar outra vez com o mesmo arquivo, os dados são recuperados.'),p('6.2 Operação diária',H2),p('<b>Produtos:</b> abrir o catálogo, selecionar Novo produto, preencher código, nome, categoria, preço e estoques e confirmar. Os ícones de lápis e lixeira permitem editar e excluir. Buscar por nome/código/categoria ou aplicar os filtros reduz a lista. Se houver vendas associadas, a exclusão é recusada; desmarcar Produto ativo impede novas vendas sem apagar o histórico.'),p('<b>Venda:</b> clicar em Nova venda, localizar os produtos, adicionar as quantidades, informar cliente opcional, pagamento e desconto e selecionar Finalizar venda. O programa apresenta o total e o comprovante interno. Uma venda sem estoque suficiente ou com desconto excessivo é recusada. O catálogo é atualizado automaticamente.'),p('<b>Histórico:</b> acessar Vendas, pesquisar o cliente ou número e aplicar um intervalo de datas. O botão de visualização abre os itens e valores históricos. Cancelar venda exige confirmação, devolve o estoque e preserva o registro com situação Cancelada. A impressão pode ser salva como PDF pelo navegador.'),p('<b>Relatórios:</b> escolher as datas inicial e final. Conferir total vendido, quantidade de vendas, ticket médio, descontos, produtos e pagamentos. Exportar CSV gera uma planilha separada por ponto e vírgula; Imprimir permite impressão ou gravação em PDF. A receita por produto é bruta; os descontos são calculados por venda. Somente vendas concluídas entram nos totais.'),p('6.3 Testes, cópia de segurança e documentos',H2),Preformatted('make test\nmake sanitize\nmake package\n\n# Ferramentas opcionais, somente para regerar documentos/UI:\npython3 scripts/setup-tools.py\nnode tests/test_ui.cjs\nPYTHONPATH=.tools/python python3 scripts/generate_docs.py',CODE),p('Os testes usam bancos separados e não alteram o arquivo de trabalho. Para uma cópia de segurança manual, encerrar o servidor antes de copiar data/vendas.db; assim, as transações em WAL são finalizadas. O arquivo data/exemplo.db acompanha a entrega com oito produtos e seis vendas fictícias. make clean remove somente objetos e executável, preservando os bancos.'),p('7 CONCLUSÃO',H1),p('A solução integra interface gráfica, servidor em C e banco persistido em arquivo, atendendo ao cadastro de produtos, registro e cálculo de vendas e relatório do total vendido. A organização em módulos e as estruturas com identificadores tornam explícita a aplicação dos conteúdos exigidos. As transações protegem os estoques, e os valores em centavos evitam erros de arredondamento nos cálculos do backend.'),p('Os testes demonstraram os fluxos descritos, a recuperação após reinício e o tratamento de entradas inválidas. As principais decisões foram adotar um único servidor local para simplificar a execução e usar bibliotecas incorporadas para não exigir instalação de banco ou pacotes de frontend. O uso de HTTP em C e a coordenação transacional dos itens são pontos que exigem estudo e domínio por todos os integrantes.'),p('O escopo é acadêmico e local, com atendimento sequencial de requisições, sem autenticação, emissão fiscal, operação remota multiusuário ou cálculo de lucro. Melhorias futuras podem incluir essas funcionalidades, desde que sejam planejadas e testadas. O relatório adota formatação acadêmica base, com papel A4, texto Times 12, entrelinhas 1,5 e margens esquerda/superior de 3 cm e direita/inferior de 2 cm. O modelo institucional específico não foi fornecido e deve ser conferido antes da submissão.'),PageBreak(),p('8 REFERÊNCIAS',H1)]
    refs=['PROJETO PRÁTICO — DESENVOLVIMENTO DE SOFTWARE EM C. Disciplina Programação de Software Básico em C. Documento de enunciado fornecido na atividade, 4 p., 2026. Arquivo: Projeto_Pratico_C_4_Pontos.pdf.','SQLITE. SQLite amalgamation, versão 3.50.4. Código-fonte e interface C. Disponível em: https://www.sqlite.org/2025/sqlite-amalgamation-3500400.zip. Cópia incorporada em vendor/sqlite; declaração de domínio público nos arquivos.','GAMBLE, Dave et al. cJSON, versão 1.7.19. Código-fonte e licença MIT. Disponível em: https://github.com/DaveGamble/cJSON/tree/v1.7.19. Cópia incorporada em vendor/cjson.','MICROSOFT. Playwright Core. Ferramenta opcional de automação do navegador. Disponível em: https://github.com/microsoft/playwright. Usada nos testes documentados.','REPORTLAB. ReportLab Toolkit. Ferramenta opcional para geração dos documentos PDF. Disponível em: https://www.reportlab.com/.','CANNY, Steve et al. python-pptx. Ferramenta opcional para geração da apresentação editável. Disponível em: https://github.com/scanny/python-pptx.','OPENAI. Codex. Assistência à elaboração do código, dos testes e dos materiais desta entrega. A equipe é responsável por revisar, adaptar e compreender integralmente o projeto.']
    for ref in refs:story += [p(plain(ref),ParagraphStyle('Reference'+str(len(story)),parent=BODY,alignment=TA_LEFT,firstLineIndent=0,leading=14,spaceAfter=14))]
    story += [PageBreak(),p('9 APÊNDICE - ROTEIRO DE APRESENTAÇÃO',H1),
              p('A identificação da equipe consta na capa. A apresentação tem 15 minutos de exposição e 5 minutos para perguntas. A distribuição abaixo organiza os temas; os responsáveis por cada etapa estão no roteiro de apoio.'),
              table(['Etapa','Conteúdo','Tempo'],[
                  ('1','Problema, objetivos e requisitos.','2 min'),
                  ('2','Arquitetura, produtos e estruturas de dados.','2 min'),
                  ('3','Regras da venda, ponteiros e memória dinâmica.','3 min'),
                  ('4','Persistência e recuperação após reiniciar.','2 min'),
                  ('5','Testes e demonstração de cadastro, venda e cancelamento.','3 min'),
                  ('6','Relatórios, resultados e encerramento.','3 min')],[1.5*cm,WIDTH-4*cm,2.5*cm]),
              p('Na demonstração, cadastrar um produto, rejeitar um código repetido, concluir uma venda com desconto, conferir o estoque e cancelar a venda. Reiniciar o servidor e verificar a recuperação dos registros. Todos devem compreender as decisões técnicas e responder às perguntas.'),
              p('Materiais de apoio: docs/apresentacao.pdf e docs/roteiro-apresentacao.txt. A relação entre os requisitos e a implementação está em docs/requisitos.md.')]
    doc.multiBuild(story)
    print('Relatório PDF gerado.')

def slide_specs():
    names='\n'.join(n+' | '+META['matriculas'][n] for n in META['integrantes'])
    return [
      dict(kicker='PROJETO PRÁTICO • LINGUAGEM C',title='Sistema de controle\nde vendas em C',body=['Projeto prático','Estácio S.A • Turma 3003','Professora: Suzane Alfaia Dias',names],image='interface-simplificada.png',speaker='Rodrigo de Sousa Barbosa',minutes='1 min',notes='Apresentar o tema, a equipe e o objetivo. Informar que o backend, as regras e a persistência são em C; a interface gráfica é no navegador.'),
      dict(kicker='01 / PROBLEMA E OBJETIVOS',title='Do cadastro ao resultado,\num fluxo integrado.',body=['Problema: registros dispersos, cálculo manual e estoque inconsistente.','Público: responsável por uma pequena loja em uso local.','Objetivo: cadastrar produtos, registrar vendas e saber o total vendido.','Aplicar structs, funções, ponteiros, alocação e persistência em C.'],speaker='Rodrigo de Sousa Barbosa',minutes='1 min',notes='Explicar um exemplo: vender duas unidades e conhecer o saldo e o faturamento sem refazer contas.'),
      dict(kicker='02 / ARQUITETURA',title='Três camadas.\nUma única aplicação local.',body=['Interface gráfica: HTML, CSS e JavaScript, sem framework.','Servidor C11/POSIX: HTTP, JSON, validações e regras de negócio.','SQLite: produtos, vendas e itens persistidos em arquivo.','Uma origem local: http://127.0.0.1:8080. Sem internet durante o uso.'],speaker='Manoel de Sousa Santos',minutes='1 min',notes='Mostrar src/, include/, web/ e vendor/. Explicar por que o banco não depende de um serviço separado.'),
      dict(kicker='03 / PRODUTOS E STRUCTS',title='Um catálogo com\nidentidade e consistência.',body=['Product: id, sku, nome, categoria, preço, estoque, mínimo, situação e notas.','Cadastrar, listar, pesquisar, atualizar e excluir.','Código único e identificador interno automático.','Produtos com vendas são desativados para preservar o histórico.'],image='02-produtos.png',speaker='Manoel de Sousa Santos',minutes='1 min',notes='Abrir include/app.h e localizar Product. Demonstrar os controles de edição e exclusão.'),
      dict(kicker='04 / REGRAS DA VENDA',title='O total é calculado em C.\nO estoque acompanha.',body=['Subtotal = soma das quantidades × preços atuais do banco.','Total = subtotal − desconto; valores inteiros em centavos.','Produto ativo, quantidade positiva e estoque suficiente.','BEGIN IMMEDIATE → validar → gravar → baixar → COMMIT.','Falha em qualquer item: ROLLBACK da operação inteira.'],speaker='Lucas Robert Lopes Silva',minutes='1 min 30 s',notes='Explicar que o frontend mostra uma prévia e o backend define os valores definitivos. Usar 2 × 24,90 + 39,90 − 9,70 = 80,00.'),
      dict(kicker='05 / PONTEIROS E MEMÓRIA',title='Memória alocada\npara cada venda.',body=['O número de itens é conhecido somente em execução.','Vetor dinâmico de SaleItem: calloc com verificação.','Ponteiros acessam itens, requisições e comandos preparados.','free em sucesso e falha; sem manter o vetor após a operação.'],code='sale.items = calloc(sale.item_count,\n                    sizeof(*sale.items));\nif (!sale.items) { /* tratar falha */ }\n\n/* ... processar itens ... */\nfree(sale.items);',speaker='Lucas Robert Lopes Silva',minutes='1 min 30 s',notes='Mostrar create_sale em src/api.c. Explicar sizeof, o ponteiro, a verificação da alocação e o caminho failed.'),
      dict(kicker='06 / PERSISTÊNCIA',title='Fechar o programa\nnão apaga a loja.',body=['Arquivo padrão: data/vendas.db.','Tabelas relacionadas, CHECKs, SKU único e chaves estrangeiras.','Nome, código e preço são copiados para cada item da venda.','Demonstração: encerrar, iniciar novamente e consultar os mesmos registros.'],speaker='Alan Freitas Miranda',minutes='2 min',notes='Executar Ctrl+C, reiniciar ./iniciar.sh e recarregar o navegador. Comparar uma venda antes/depois. Não apagar o banco nem usar reset.'),
      dict(kicker='07 / TESTES E EVIDÊNCIAS',title='Resultados executados,\ncom evidências.',body=[f'{API["total"]} testes da API e do SQLite: aprovados.',f'{UI["total"]} fluxos no Chrome: aprovados.','ASan/UBSan: mesmos 18 testes, sem erros detectados nos módulos próprios.','Casos: vazio, código repetido, estoque, desconto, cancelamento e reinício.','JSON, capturas e relatórios exportados em artifacts/.'],speaker='Gabriel Henrique Maciel Leite',minutes='1 min',notes='Abrir os JSON e explicar o escopo. As bibliotecas incorporadas não foram instrumentadas pelos sanitizers.'),
      dict(kicker='08 / DEMONSTRAÇÃO AO VIVO',title='Uma venda, do início\nao relatório.',body=['1. Cadastrar um produto e pesquisar seu código.','2. Repetir o código: mostrar a rejeição e explicar a validação.','3. Adicionar itens, informar desconto e finalizar uma venda.','4. Conferir o comprovante e a quantidade restante.','5. Cancelar a venda: conferir a devolução única ao estoque.'],image='03-nova-venda.png',speaker='Gabriel Henrique Maciel Leite',minutes='2 min',notes='Usar SKU DEMO-AULA, preço 10,00, estoque 5 e vender duas unidades com desconto de 1,00. Total esperado 19,00. Todos os dados de demonstração são fictícios.'),
      dict(kicker='09 / RELATÓRIOS',title='O movimento da loja,\nem números claros.',body=['Período de datas no horário de Belém (UTC−3).','Total líquido, vendas, ticket médio, descontos e unidades.','Ranking por unidades e receita bruta dos produtos.','Formas de pagamento, exportação CSV e impressão em PDF.','Vendas canceladas ficam no histórico e não entram nos totais.'],image='04-relatorios.png',speaker='Jorge Igor Dos Santos Pinto',minutes='1 min 30 s',notes='Comparar o relatório com uma venda e explicar a diferença entre receita bruta dos produtos e total após descontos.'),
      dict(kicker='10 / RESULTADOS E LIMITES',title='O essencial entregue.\nOs próximos passos, claros.',body=['Entregue: C modular, CRUD gráfico, venda, relatório e persistência.','Execução simples: make e ./iniciar.sh.','Escopo: local, atendimento sequencial e controle interno.','Melhorias futuras: usuários, operação remota e emissão fiscal.','Toda a equipe deve compreender e explicar o código.'],speaker='Jorge Igor Dos Santos Pinto',minutes='1 min',notes='Não afirmar homologação de produção. Mencionar que curso/cidade e conformidade com modelo institucional precisam de revisão.'),
      dict(kicker='PERGUNTAS • 5 MINUTOS',title='Cada venda conta.\nCada decisão tem uma razão.',body=['Por que centavos inteiros?','Como o programa evita uma venda parcial?','Onde a memória é alocada e liberada?','O que garante a recuperação após reiniciar?','Obrigado.'],speaker='Jorge Igor Dos Santos Pinto',minutes='30 s + perguntas',notes='Encerrar a exposição em 15 minutos e abrir cinco minutos para perguntas, conforme o enunciado.'),
    ]

def fit_image(image,width,height):
    from PIL import Image as PILImage
    with PILImage.open(image) as file:w,h=file.size
    scale=min(width/w,height/h)
    return w*scale,h*scale

def slides(pdf_only=False):
    deck=None if pdf_only else Presentation()
    if deck is not None:
        deck.slide_width=Inches(13.333);deck.slide_height=Inches(7.5)
    pdf=canvas.Canvas(str(DOCS/'apresentacao.pdf'),pagesize=(960,540))
    pdf.setTitle('Venda. — Sistema de controle de vendas em C');pdf.setAuthor('; '.join(META['integrantes']))
    specs=slide_specs()
    def rgb(value):return RGBColor.from_string(value.lstrip('#'))
    for i,spec in enumerate(specs):
        slide=None
        if deck is not None:
            slide=deck.slides.add_slide(deck.slide_layouts[6]);slide.background.fill.solid();slide.background.fill.fore_color.rgb=rgb('#f8f9fb')
        pdf.setFillColor(colors.HexColor('#f8f9fb'));pdf.rect(0,0,960,540,fill=1,stroke=0)
        def rectangle(x,y,w,h,color):
            if slide is not None:
                shape=slide.shapes.add_shape(MSO_SHAPE.RECTANGLE,Inches(x),Inches(y),Inches(w),Inches(h));shape.fill.solid();shape.fill.fore_color.rgb=rgb(color);shape.line.fill.background()
            pdf.setFillColor(colors.HexColor(color));pdf.rect(x*72,540-(y+h)*72,w*72,h*72,stroke=0,fill=1)
        def text(x,y,w,h,value,size=20,color='#25303b',bold=False,font='Arial'):
            shape=None
            if slide is not None:
                shape=slide.shapes.add_textbox(Inches(x),Inches(y),Inches(w),Inches(h));tf=shape.text_frame;tf.clear();tf.word_wrap=True;tf.margin_left=0;tf.margin_top=0;tf.margin_right=0;tf.margin_bottom=0
                for k,line in enumerate(value.split('\n')):
                    para=tf.paragraphs[0] if k==0 else tf.add_paragraph();para.text=line;para.font.name=font;para.font.size=Pt(size);para.font.bold=bold;para.font.color.rgb=rgb(color);para.space_after=Pt(0)
            # Os textos são quebrados antes de desenhar para caber nas duas saídas.
            from reportlab.lib.utils import simpleSplit
            f='Courier' if font=='Courier New' else 'Helvetica-Bold' if bold else 'Helvetica'
            pdf.setFont(f,size);pdf.setFillColor(colors.HexColor(color));yy=540-y*72-size
            for line in value.split('\n'):
                for part in simpleSplit(line,f,size,w*72):pdf.drawString(x*72,yy,part);yy-=size*1.2
            return shape
        rectangle(0,0,.12,7.5,'#ed663f')
        text(.62,.43,11.9,.3,spec['kicker'],10,'#ed663f',True)
        text(.62,1.05,12,1.5,spec['title'],32,'#25303b',True)
        has_visual=bool(spec.get('image') or spec.get('code'))
        body_w=6.2 if has_visual else 11.5
        ypos=2.9
        for j,line in enumerate(spec['body']):
            if i==0:
                size=13 if j<3 else 10;gap=.55 if j<3 else 1.2
                text(.66,ypos,body_w,1.3 if j==3 else .7,line,size,'#77808d' if j else '#25303b',j==0)
            else:
                rectangle(.68,ypos+.08,.055,.18,'#ed663f')
                text(.92,ypos,body_w-.2,.72,line,16 if not has_visual else 13.5,'#596575')
                gap=.76 if not has_visual else .77
            ypos+=gap
        if spec.get('image'):
            image=ART/spec['image'];iw,ih=fit_image(image,5.25*72,4.15*72)
            x=7.46+(5.25-iw/72)/2;y=2.55
            if slide is not None: slide.shapes.add_picture(str(image),Inches(x),Inches(y),width=Inches(iw/72),height=Inches(ih/72))
            pdf.drawImage(str(image),x*72,540-y*72-ih,iw,ih)
        elif spec.get('code'):
            rectangle(7.2,2.9,5.4,2.9,'#25303b');text(7.5,3.25,4.85,2.4,spec['code'],12,'#ffffff',False,'Courier New')
        rectangle(.62,7.03,12.1,.012,'#e4e7ec')
        text(.65,7.16,10,.2,'VENDA.   |   Sistema de controle de vendas em C',8,'#9099a6')
        text(12.05,7.12,.65,.3,f'{i+1:02d} / {len(specs):02d}',9,'#9099a6')
        if slide is not None: slide.notes_slide.notes_text_frame.text=spec['notes']
        pdf.showPage()
    if deck is not None: deck.save(DOCS/'apresentacao.pptx')
    pdf.save()
    script=['ROTEIRO DE APRESENTAÇÃO — 15 MINUTOS + 5 DE PERGUNTAS','Estácio S.A | Turma 3003 | Professora Suzane Alfaia Dias','',
    'Foram informados seis integrantes; o PDF prevê grupos de cinco. Confirmar a composição com a professora.','Curso e cidade: preencher em docs/equipe.json. A divisão abaixo é sugestão para estudo, não comprovação de contribuições.','',
    'EQUIPE E MATRÍCULAS',*[n+' | Matrícula: '+META['matriculas'][n] for n in META['integrantes']],'','PREPARAÇÃO','Executar ./iniciar.sh --demo em um banco vazio, ou usar --db data/exemplo.db --port 8081.','Abrir o navegador no endereço indicado; deixar src/api.c e include/app.h disponíveis.','Conferir que o SKU DEMO-AULA ainda não existe; usar outro código único se necessário.','']
    for i,spec in enumerate(specs):script += [f'SLIDE {i+1:02d} — {spec["title"].replace(chr(10)," ")} ',f'Apresenta: {spec["speaker"]}. Tempo: {spec["minutes"]}.',spec['notes'],'']
    script += ['RESPOSTAS QUE TODOS DEVEM DOMINAR','1. Centavos inteiros evitam arredondamento binário de valores monetários.','2. BEGIN IMMEDIATE, COMMIT e ROLLBACK unem a gravação da venda à baixa de todos os itens.','3. create_sale aloca o vetor SaleItem com calloc, verifica o retorno e libera em sucesso/falha.','4. SQLite recupera o mesmo arquivo em cada execução; os testes encerram e reabrem um processo real.','5. Cancelar não apaga: preserva histórico e devolve estoque uma única vez.','6. O backend em C recalcula o valor; a prévia JavaScript não define o preço definitivo.','7. Gráficos do relatório usam horário de Belém; o banco guarda timestamps em UTC.','8. Escopo atual: local, sem emissão fiscal e sem autenticação remota.','',
    'DISTRIBUIÇÃO DOS 15 MINUTOS','Rodrigo de Sousa Barbosa: 2 min. Manoel de Sousa Santos: 2 min. Lucas Robert Lopes Silva: 3 min.','Alan Freitas Miranda: 2 min. Gabriel Henrique Maciel Leite: 3 min. Jorge Igor Dos Santos Pinto: 3 min.','Após a exposição: 5 min para perguntas.']
    (DOCS/'roteiro-apresentacao.txt').write_text('\n'.join(script)+'\n')
    print('Apresentação PDF e roteiro gerados.' if pdf_only else 'Slides PPTX/PDF e roteiro gerados.')

if __name__=='__main__':
    import sys
    report();slides(pdf_only='--pdf-only' in sys.argv)
    from generate_sales_pdf import sales_report
    sales_report()
