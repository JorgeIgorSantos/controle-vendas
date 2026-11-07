#!/usr/bin/env python3
"""Integração real HTTP + executável C + arquivo SQLite, sem bibliotecas Python externas."""
import copy
import datetime
from html.parser import HTMLParser
import http.client
import json
import os
from pathlib import Path
import shutil
import signal
import socket
import sqlite3
import subprocess
import time
import unittest

ROOT = Path(__file__).resolve().parents[1]
BINARY = ROOT / os.environ.get('VENDA_BINARY','build/vendas')
RUNTIME = ROOT / 'tests' / '.runtime'
RUNTIME.mkdir(exist_ok=True)
RESULTS = []


class IntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.db = RUNTIME / 'integration.db'
        for suffix in ['', '-wal', '-shm']:
            Path(str(cls.db) + suffix).unlink(missing_ok=True)
        with socket.socket() as sock:
            sock.bind(('127.0.0.1', 0))
            cls.port = sock.getsockname()[1]
        cls.start()

    @classmethod
    def start(cls):
        cls.log = open(RUNTIME / 'server.log', 'a', encoding='utf-8')
        cls.process = subprocess.Popen([str(BINARY), '--port', str(cls.port), '--db', str(cls.db)], cwd=ROOT, stdout=cls.log, stderr=cls.log)
        for _ in range(100):
            if cls.process.poll() is not None:
                raise RuntimeError((RUNTIME/'server.log').read_text())
            try:
                if cls.request('GET', '/api/health')[0] == 200:
                    return
            except OSError:
                time.sleep(.05)
        raise RuntimeError('Servidor não iniciou em 5 segundos')

    @classmethod
    def stop(cls):
        if cls.process.poll() is None:
            cls.process.send_signal(signal.SIGTERM)
        cls.process.wait(timeout=10)
        cls.log.close()
        if cls.process.returncode != 0:
            raise RuntimeError((RUNTIME/'server.log').read_text())

    @classmethod
    def tearDownClass(cls):
        cls.stop()

    @classmethod
    def request(cls, method, path, data=None, headers=None):
        body = json.dumps(data, ensure_ascii=False).encode() if data is not None else None
        conn = http.client.HTTPConnection('127.0.0.1', cls.port, timeout=7)
        conn.request(method, path, body=body, headers={'Content-Type':'application/json', **(headers or {})})
        response = conn.getresponse()
        content = response.read()
        status = response.status
        conn.close()
        return status, json.loads(content) if content else None

    def run(self, result=None):
        before = len(result.failures) + len(result.errors) if result else 0
        super().run(result)
        after = len(result.failures) + len(result.errors) if result else 0
        RESULTS.append({'test':self.id().split('.')[-1], 'description':self.shortDescription() or '', 'result':'APROVADO' if before == after else 'FALHOU'})

    def product(self, sku=None, **overrides):
        data = {'sku':sku or self.id().split('.')[-1], 'name':'Café especial', 'category':'Mercearia', 'price_cents':2490, 'stock':10, 'active':True}
        data.update(overrides)
        status, created = self.request('POST', '/api/products', data)
        self.assertEqual(status, 201, created)
        return created

    def sale(self, products, **overrides):
        data = {'customer':'Cliente teste', 'payment_method':'pix','items':[{'product_id':p['id'],'quantity':q} for p,q in products]}
        data.update(overrides)
        return self.request('POST','/api/sales',data)

    def test_01_empty_database(self):
        """Banco vazio retorna listas e totais zerados sem erro."""
        self.assertEqual(self.request('GET','/api/products'),(200,[]))
        self.assertEqual(self.request('GET','/api/sales'),(200,[]))
        report = self.request('GET','/api/reports')[1]
        self.assertEqual(report['summary']['total_cents'],0)
        self.assertEqual(report['summary']['sale_count'],0)

    def test_02_product_crud(self):
        """Cadastro, listagem, pesquisa, atualização e exclusão funcionam."""
        p=self.product('CRUD-001')
        self.assertEqual(self.request('GET',f"/api/products/{p['id']}")[1]['name'],'Café especial')
        self.assertEqual(len(self.request('GET','/api/products?search=CRUD-001')[1]),1)
        p.update(name='Café atualizado',price_cents=2990,active=False)
        status,updated=self.request('PUT',f"/api/products/{p['id']}",p)
        self.assertEqual(status,200)
        self.assertEqual(updated['price_cents'],2990)
        self.assertEqual(updated['active'],0)
        self.assertEqual(self.request('DELETE',f"/api/products/{p['id']}")[0],200)
        self.assertEqual(self.request('GET',f"/api/products/{p['id']}")[0],404)

    def test_03_duplicate_identifier(self):
        """Código duplicado é rejeitado, inclusive com letras em caixa diferente."""
        p=self.product('DUP-001')
        self.assertEqual(self.request('POST','/api/products',{**p,'sku':'dup-001'})[0],409)
        other=self.product('DUP-002')
        self.assertEqual(self.request('PUT',f"/api/products/{other['id']}",{**other,'sku':'DUP-001'})[0],409)

    def test_04_invalid_product(self):
        """Campos vazios, preços inválidos e estoques fracionários/negativos são rejeitados."""
        valid={'sku':'INVALID','name':'Produto','category':'Categoria','price_cents':100,'stock':1,'active':True}
        for field, values in {'sku':['','   ','x'*41],'name':['',None,'x'*121],'category':[''],'price_cents':[0,-1,1.5,'10',100000001],'stock':[-1,1.2,1000001],'active':['true',2]}.items():
            for value in values:
                with self.subTest(field=field,value=value):
                    self.assertEqual(self.request('POST','/api/products',{**valid,field:value})[0],400)

    def test_05_sale_total_stock_snapshot(self):
        """Venda calcula total no servidor, baixa estoque e preserva preço/nome histórico."""
        a=self.product('SALE-A',price_cents=2490,stock=10)
        b=self.product('SALE-B',price_cents=3990,stock=10)
        status,sale=self.sale([(a,2),(b,1)],total_cents=1)
        self.assertEqual(status,201,sale)
        self.assertEqual(sale['subtotal_cents'],8970)
        self.assertEqual(sale['total_cents'],8970)
        self.assertEqual(self.request('GET',f"/api/products/{a['id']}")[1]['stock'],8)
        self.request('PUT',f"/api/products/{a['id']}",{**a,'price_cents':9900,'name':'Novo nome','stock':8})
        detail=self.request('GET',f"/api/sales/{sale['id']}")[1]
        self.assertEqual(detail['items'][0]['unit_price_cents'],2490)
        self.assertEqual(detail['items'][0]['name'],'Café especial')
        self.assertEqual(detail['total_cents'],8970)
        self.assertEqual(self.request('DELETE',f"/api/products/{a['id']}")[0],409)

    def test_06_insufficient_stock_atomicity(self):
        """Falha em um item não altera estoque de nenhum produto nem registra venda parcial."""
        a=self.product('ATOMIC-A',stock=4)
        b=self.product('ATOMIC-B',stock=1)
        before=len(self.request('GET','/api/sales')[1])
        self.assertEqual(self.sale([(a,2),(b,2)])[0],409)
        self.assertEqual(self.request('GET',f"/api/products/{a['id']}")[1]['stock'],4)
        self.assertEqual(self.request('GET',f"/api/products/{b['id']}")[1]['stock'],1)
        self.assertEqual(len(self.request('GET','/api/sales')[1]),before)

    def test_07_invalid_sale(self):
        """Venda vazia, item repetido, quantidade inválida, pagamento e desconto são validados."""
        p=self.product('BAD-SALE')
        for override in [{'items':[]},{'payment_method':'fiado'},{'discount_cents':-1},{'discount_cents':999999},{'items':[{'product_id':p['id'],'quantity':0}]},{'items':[{'product_id':p['id'],'quantity':1.5}]},{'items':[{'product_id':p['id'],'quantity':1},{'product_id':p['id'],'quantity':1}]}]:
            with self.subTest(override=override): self.assertEqual(self.sale([(p,1)],**override)[0],400)
        self.assertEqual(self.sale([({'id':2147483647},1)])[0],404)
        self.request('PUT',f"/api/products/{p['id']}",{**p,'active':False})
        self.assertEqual(self.sale([(p,1)])[0],409)

    def test_08_sale_has_no_cancellation_action(self):
        """A versão enxuta recusa a rota removida e conserva a venda concluída."""
        product = self.product('SEM-CANCELAMENTO')
        status, sale = self.sale([(product, 3)])
        self.assertEqual(status, 201)
        self.assertEqual(self.request('POST', f"/api/sales/{sale['id']}/cancel", {})[0], 404)
        self.assertEqual(self.request('GET', f"/api/sales/{sale['id']}")[1]['status'], 'completed')
        self.assertEqual(self.request('GET', f"/api/products/{product['id']}")[1]['stock'], 7)

    def test_09_reports_and_filters(self):
        """Relatório agrega exatamente vendas concluídas; filtros de data e busca funcionam."""
        sales=self.request('GET','/api/sales')[1]
        report=self.request('GET','/api/reports')[1]
        completed=[s for s in sales if s['status']=='completed']
        self.assertEqual(report['summary']['total_cents'],sum(s['total_cents'] for s in completed))
        self.assertEqual(report['summary']['sale_count'],len(completed))
        self.assertEqual(set(report), {'from', 'to', 'summary'})
        self.assertEqual(set(report['summary']), {'sale_count', 'total_cents'})
        self.assertEqual(self.request('GET','/api/reports?from=1900-01-01&to=1900-01-02')[1]['summary']['total_cents'],0)
        for query in ['from=2026-02-30','from=2026-13-01','from=2026-10-30&to=2026-10-01','from=x','from=2026-1-01']:
            self.assertEqual(self.request('GET','/api/reports?'+query)[0],400)
        self.assertEqual(self.request('GET','/api/products?status=invalid')[0],400)

    def test_10_missing_and_invalid_routes(self):
        """Registros inexistentes, métodos inválidos e arquivos fora da interface não são expostos."""
        for method,path in [('GET','/api/products/999999'),('DELETE','/api/products/999999'),('PUT','/api/sales/1'),('GET','/api/sales/999999'),('POST','/api/sales/999999/cancel'),('GET','/api/unknown'),('GET','/../data/vendas.db'),('GET','/data/vendas.db'),('GET','/src/main.c')]:
            with self.subTest(path=path):self.assertIn(self.request(method,path,{} if method=='POST' else None)[0],[404,405])

    def test_11_persistence_after_restart(self):
        """Reiniciar o executável recupera produtos, vendas e relatório do mesmo arquivo SQLite."""
        before_products=self.request('GET','/api/products')[1]
        before_sales=self.request('GET','/api/sales')[1]
        before_report=self.request('GET','/api/reports')[1]
        self.__class__.stop();self.__class__.start()
        self.assertEqual(self.request('GET','/api/products')[1],before_products)
        self.assertEqual(self.request('GET','/api/sales')[1],before_sales)
        self.assertEqual(self.request('GET','/api/reports')[1],before_report)
        with sqlite3.connect(self.db) as conn:
            self.assertEqual(conn.execute('PRAGMA integrity_check').fetchone()[0],'ok')
            self.assertEqual(conn.execute('PRAGMA foreign_key_check').fetchall(),[])

    def test_12_local_origin_and_malformed_json(self):
        """Origem externa, JSON malformado e conteúdo não JSON são recusados."""
        self.assertEqual(self.request('POST','/api/products',{},headers={'Origin':'https://outro-site.example'})[0],403)
        self.assertEqual(self.request('POST','/api/products',{},headers={'Content-Type':'text/plain'})[0],415)
        for body in [b'{broken',b'[]',b'{} trailing',b'{"sku":"x"}\x00']:
            conn=http.client.HTTPConnection('127.0.0.1',self.port,timeout=7)
            conn.request('POST','/api/products',body=body,headers={'Content-Type':'application/json'})
            response=conn.getresponse();response.read();self.assertEqual(response.status,400);conn.close()

    def test_13_money_precision(self):
        """Cálculo inteiro mantém a precisão de centavos (3 × R$ 0,10)."""
        p=self.product('PRECISION',price_cents=10,stock=10)
        status,sale=self.sale([(p,3)])
        self.assertEqual(status,201)
        self.assertEqual(sale['subtotal_cents'],30)
        self.assertEqual(sale['total_cents'],30)

    def test_14_database_constraints(self):
        """O banco também recusa estoque negativo e código duplicado, protegendo a integridade."""
        with sqlite3.connect(self.db) as conn:
            with self.assertRaises(sqlite3.IntegrityError):conn.execute("UPDATE products SET stock=-1 WHERE id=(SELECT min(id) FROM products)")
            with self.assertRaises(sqlite3.IntegrityError):conn.execute("INSERT INTO products(sku,name,category,price_cents,stock,min_stock) SELECT sku,name,category,price_cents,stock,min_stock FROM products LIMIT 1")

    def test_15_static_interface(self):
        """Servidor C entrega o HTML e os arquivos gerados no build do Angular."""
        class AssetParser(HTMLParser):
            def handle_starttag(self, tag, attributes):
                attrs = dict(attributes)
                if tag == 'script' and attrs.get('src'):
                    assets[attrs['src']] = 'text/javascript'
                if tag == 'link' and attrs.get('rel') == 'stylesheet':
                    assets[attrs['href']] = 'text/css'

        def get_asset(path, mime):
            conn = http.client.HTTPConnection('127.0.0.1', self.port, timeout=7)
            try:
                conn.request('GET', path)
                res = conn.getresponse()
                content = res.read()
                self.assertEqual(res.status, 200)
                self.assertIn(mime, res.getheader('Content-Type'))
                self.assertIn("frame-ancestors 'none'", res.getheader('Content-Security-Policy'))
                self.assertTrue(content)
                return content
            finally:
                conn.close()

        assets = {}
        html = get_asset('/', 'text/html').decode()
        self.assertIn('<app-root>', html)
        AssetParser().feed(html)
        self.assertEqual(set(assets.values()), {'text/javascript', 'text/css'})
        for path, mime in assets.items():
            get_asset('/' + path.lstrip('/'), mime)
        get_asset('/favicon.svg', 'image/svg+xml')
        for path in ('/src/main.ts', '/../main.js', '/%2e%2e/main.js', '/package.json'):
            self.assertEqual(self.request('GET', path)[0], 404)

    def test_17_existing_database(self):
        """Banco antigo aceita novas operações e preserva descontos e cancelamentos históricos."""
        cls = type(self)
        original_db = cls.db
        legacy_db = RUNTIME / 'legacy.db'
        for suffix in ('', '-wal', '-shm'):
            Path(str(legacy_db) + suffix).unlink(missing_ok=True)
        shutil.copyfile(ROOT / 'data' / 'exemplo.db', legacy_db)
        with sqlite3.connect(legacy_db) as conn:
            conn.execute("UPDATE sales SET status='cancelled', cancelled_at=created_at WHERE id=2")

        cls.stop()
        cls.db = legacy_db
        try:
            cls.start()
            self.assertEqual(len(self.request('GET', '/api/products')[1]), 8)
            self.assertEqual(self.request('GET', '/api/sales/2')[1]['status'], 'cancelled')
            self.assertEqual(self.request('GET', '/api/sales/6')[1]['discount_cents'], 970)
            self.assertEqual(self.request('GET', '/api/reports')[1]['summary'],
                             {'sale_count': 5, 'total_cents': 49590 - 8490})
            product = self.product('NOVO-EM-BANCO-ANTIGO')
            self.assertEqual(self.sale([(product, 1)])[0], 201)
        finally:
            try:
                cls.stop()
            finally:
                cls.db = original_db
                cls.start()

    def test_18_shutdown_saves_database(self):
        """Opção da interface encerra o servidor com sucesso e preserva o arquivo."""
        self.assertEqual(self.request('POST','/api/shutdown',{})[0],200)
        self.__class__.process.wait(timeout=10)
        self.assertEqual(self.__class__.process.returncode,0)
        self.__class__.log.close()
        self.__class__.start()
        self.assertTrue(self.request('GET','/api/products')[1])


if __name__=='__main__':
    suite=unittest.defaultTestLoader.loadTestsFromTestCase(IntegrationTests)
    result=unittest.TextTestRunner(verbosity=2).run(suite)
    sanitized='ASAN_OPTIONS' in os.environ
    evidence={'executed_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'command':'make sanitize' if sanitized else 'make test','total':result.testsRun,'failures':len(result.failures),'errors':len(result.errors),'tests':RESULTS}
    qa = ROOT / 'artifacts' / 'qa'
    qa.mkdir(exist_ok=True)
    (qa / ('sanitizer-test-results.json' if sanitized else 'test-results.json')).write_text(json.dumps(evidence,ensure_ascii=False,indent=2),encoding='utf-8')
    raise SystemExit(not result.wasSuccessful())
