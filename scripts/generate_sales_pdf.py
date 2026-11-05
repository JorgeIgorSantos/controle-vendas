#!/usr/bin/env python3
"""Gera um relatório compacto com dados somente de data/exemplo.db."""
from pathlib import Path
import sqlite3
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from xml.sax.saxutils import escape

ROOT = Path(__file__).resolve().parents[1]
PAYMENTS = {'credito':'Cartão de crédito', 'debito':'Cartão de débito', 'pix':'Pix', 'dinheiro':'Dinheiro'}

def money(cents):
    return ('R$ '+format(cents/100, ',.2f')).replace(',', '_').replace('.', ',').replace('_', '.')

def sales_report():
    with sqlite3.connect((ROOT/'data/exemplo.db').as_uri()+'?mode=ro', uri=True) as db:
        db.row_factory=sqlite3.Row
        sales=db.execute("SELECT * FROM sales WHERE status='completed' ORDER BY id").fetchall()
        products=db.execute("SELECT i.sku, i.name, SUM(i.quantity) quantity, SUM(i.total_cents) gross FROM sale_items i JOIN sales s ON s.id=i.sale_id WHERE s.status='completed' GROUP BY i.sku,i.name ORDER BY quantity DESC,gross DESC LIMIT 10").fetchall()
        payments=db.execute("SELECT payment_method,COUNT(*) count,SUM(total_cents) total FROM sales WHERE status='completed' GROUP BY payment_method ORDER BY total DESC").fetchall()
    assert sales, 'O banco de exemplo não contém vendas concluídas.'
    total=sum(s['total_cents'] for s in sales)
    discount=sum(s['discount_cents'] for s in sales)
    units=sum(p['quantity'] for p in products)
    assert sum(p['total'] for p in payments)==total
    assert sum(p['gross'] for p in products)-discount==total
    start=min(s['created_at'][:10] for s in sales)
    end=max(s['created_at'][:10] for s in sales)
    date=lambda value: '/'.join(reversed(value.split('-')))
    dest=ROOT/'artifacts/relatorio-vendas-exemplo.pdf'
    doc=SimpleDocTemplate(str(dest),pagesize=A4,leftMargin=2*cm,rightMargin=2*cm,topMargin=1.6*cm,bottomMargin=1.6*cm,title='Relatório de vendas - dados de exemplo',author='Venda.')
    width=A4[0]-4*cm
    base=ParagraphStyle('Body',fontName='Helvetica',fontSize=9,leading=13,textColor=colors.HexColor('#25303b'))
    heading=ParagraphStyle('Heading',parent=base,fontName='Helvetica-Bold',fontSize=12,leading=16,spaceBefore=16,spaceAfter=8)
    title=ParagraphStyle('Title',parent=heading,fontSize=21,leading=25,spaceBefore=0,spaceAfter=7)
    muted=ParagraphStyle('Muted',parent=base,fontSize=8,textColor=colors.HexColor('#697381'))
    def para(value,style=base):return Paragraph(escape(str(value)),style)
    def grid(headers,rows,widths):
        content=[[para(h) for h in headers]]+[[para(v) for v in row] for row in rows]
        t=Table(content,colWidths=widths,repeatRows=1,hAlign='LEFT')
        t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#f1f3f5')),('VALIGN',(0,0),(-1,-1),'TOP'),('LEFTPADDING',(0,0),(-1,-1),8),('RIGHTPADDING',(0,0),(-1,-1),8),('TOPPADDING',(0,0),(-1,-1),7),('BOTTOMPADDING',(0,0),(-1,-1),7),('LINEBELOW',(0,0),(-1,0),.6,colors.HexColor('#d5dbe1')),('LINEBELOW',(0,1),(-1,-1),.3,colors.HexColor('#e6eaee'))]))
        return t
    story=[para('Relatório de vendas',title),para('Dados fictícios do banco de exemplo',muted),Spacer(1,.3*cm),para('Período: '+date(start)+' a '+date(end)),para('Somente vendas concluídas. Valores em reais (R$).',muted),Spacer(1,.4*cm),grid(['Total vendido','Vendas','Unidades','Ticket médio'],[[money(total),len(sales),units,money(round(total/len(sales)))]],[width/4]*4),para('Formas de pagamento',heading),grid(['Forma de pagamento','Vendas','Total'],[(PAYMENTS[r['payment_method']],r['count'],money(r['total'])) for r in payments],[width*.5,width*.2,width*.3]),para('Produtos vendidos',heading),grid(['Produto','Código','Unidades','Receita bruta'],[(r['name'],r['sku'],r['quantity'],money(r['gross'])) for r in products],[width*.43,width*.19,width*.14,width*.24]),Spacer(1,.35*cm),para('Descontos concedidos: '+money(discount)),Spacer(1,.15*cm),para('A receita dos produtos é bruta. O total vendido considera os descontos aplicados às vendas. Fonte: data/exemplo.db.',muted)]
    def footer(c,d):
        c.setFont('Helvetica',8);c.setFillColor(colors.HexColor('#697381'));c.drawString(2*cm,1*cm,'Venda. | Relatório de exemplo');c.drawRightString(A4[0]-2*cm,1*cm,str(d.page))
    doc.build(story,onFirstPage=footer,onLaterPages=footer)
    print('Relatório de vendas de exemplo gerado.')

if __name__=='__main__':sales_report()
