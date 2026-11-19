#!/usr/bin/env python3
"""Verifica o servidor real atrás de HTTPS e de um domínio público configurado."""
import http.client
import json
import os
from pathlib import Path
import signal
import socket
import subprocess
import tempfile
import time
import unittest

ROOT = Path(__file__).resolve().parents[1]
BINARY = ROOT / os.environ.get('VENDA_BINARY', 'build/vendas')
RUNTIME = ROOT / 'tests' / '.runtime'
RUNTIME.mkdir(exist_ok=True)
PUBLIC_HOST = 'controle-vendas-test.onrender.com'


class DeploymentTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory(dir=RUNTIME, prefix='deploy-')
        self.addCleanup(self.directory.cleanup)
        with socket.socket() as sock:
            sock.bind(('127.0.0.1', 0))
            self.port = sock.getsockname()[1]
        self.environment = dict(os.environ)
        for name in ('PORT', 'VENDA_PUBLIC_HOST', 'RENDER_EXTERNAL_HOSTNAME'):
            self.environment.pop(name, None)
        self.environment.update(PORT=str(self.port), RENDER_EXTERNAL_HOSTNAME=PUBLIC_HOST)
        self.start()
        self.addCleanup(self.stop)

    def start(self, arguments=()):
        self.process = subprocess.Popen(
            [str(BINARY), '--host', '127.0.0.1', '--db', str(Path(self.directory.name) / 'vendas.db'), *arguments],
            cwd=ROOT, env=self.environment, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        )
        for _ in range(100):
            if self.process.poll() is not None:
                raise RuntimeError(self.process.stdout.read().decode())
            try:
                if self.request('GET', '/api/health', host='127.0.0.1:' + str(self.port))[0] == 200:
                    return
            except OSError:
                time.sleep(.05)
        raise RuntimeError('Servidor não iniciou na porta configurada.')

    def stop(self):
        if self.process.poll() is None:
            self.process.send_signal(signal.SIGTERM)
        output = self.process.communicate(timeout=10)[0].decode()
        if self.process.returncode != 0:
            raise RuntimeError(output)

    def request(self, method, path, data=None, host=PUBLIC_HOST, origin=None, headers=None):
        request_headers = {'Host': host, 'Content-Type': 'application/json', **(headers or {})}
        if origin is not None:
            request_headers['Origin'] = origin
        connection = http.client.HTTPConnection('127.0.0.1', self.port, timeout=5)
        try:
            connection.request(method, path, body=json.dumps(data) if data is not None else None, headers=request_headers)
            response = connection.getresponse()
            return response.status, response.read(), response.getheader('Content-Type')
        finally:
            connection.close()

    def test_public_health_and_frontend(self):
        """PORT e o domínio do Render permitem acessar a API e o Angular."""
        for host in (PUBLIC_HOST, PUBLIC_HOST.upper(), PUBLIC_HOST + ':443'):
            self.assertEqual(self.request('GET', '/api/health', host=host)[0], 200)
        status, body, content_type = self.request('GET', '/')
        self.assertEqual(status, 200)
        self.assertIn('text/html', content_type)
        self.assertIn(b'<app-root>', body)

    def test_sale_from_https_origin(self):
        """Uma origem HTTPS autorizada cadastra, vende e consulta os totais."""
        origin = 'https://' + PUBLIC_HOST
        data = {'sku': 'DEPLOY-001', 'name': 'Produto', 'category': 'Teste', 'price_cents': 2490, 'stock': 5}
        status, body, _ = self.request('POST', '/api/products', data, origin=origin)
        self.assertEqual(status, 201, body)
        product = json.loads(body)
        sale = {'payment_method': 'pix', 'items': [{'product_id': product['id'], 'quantity': 2}]}
        status, body, _ = self.request('POST', '/api/sales', sale, origin=origin)
        self.assertEqual(status, 201, body)
        self.assertEqual(json.loads(body)['total_cents'], 4980)
        self.assertEqual(json.loads(self.request('GET', '/api/products')[1])[0]['stock'], 3)
        report = json.loads(self.request('GET', '/api/reports')[1])
        self.assertEqual(report['summary'], {'sale_count': 1, 'total_cents': 4980})

    def test_other_hosts_and_origins_are_rejected(self):
        """Outros hosts, origens e cabeçalhos encaminhados não liberam acesso."""
        for host in ('outro.example', PUBLIC_HOST + '.outro.example', PUBLIC_HOST + ':10000'):
            self.assertEqual(self.request('GET', '/api/health', host=host)[0], 403)
        for origin in ('null', 'http://' + PUBLIC_HOST, 'https://' + PUBLIC_HOST + '.outro.example',
                       'https://' + PUBLIC_HOST + '/path', 'https://outro.example'):
            self.assertEqual(self.request('POST', '/api/products', {}, origin=origin)[0], 403)
        self.assertEqual(self.request('GET', '/api/health', host='outro.example',
                                     headers={'X-Forwarded-Host': PUBLIC_HOST})[0], 403)
        self.assertEqual(self.request('GET', '/api/health', headers={'Sec-Fetch-Site': 'cross-site'})[0], 403)

    def test_remote_shutdown_is_disabled(self):
        """Um visitante não consegue encerrar o servidor hospedado."""
        self.assertEqual(self.request('POST', '/api/shutdown', origin='https://' + PUBLIC_HOST)[0], 403)
        self.assertEqual(self.request('GET', '/api/health')[0], 200)

    def test_custom_domain_and_cli_port_override(self):
        """Domínio explícito e --port prevalecem sobre os valores da plataforma."""
        self.stop()
        self.environment.update(VENDA_PUBLIC_HOST='vendas.example', PORT='invalid')
        self.start(['--port', str(self.port)])
        self.assertEqual(self.request('GET', '/api/health', host='vendas.example', origin='https://vendas.example')[0], 200)
        self.assertEqual(self.request('GET', '/api/health')[0], 403)

    def test_invalid_configuration_fails_before_start(self):
        """Porta inválida ou domínio com protocolo/caminho impedem a inicialização."""
        for overrides in ({'PORT': '0'}, {'PORT': '65536'}, {'PORT': 'invalid'},
                          {'VENDA_PUBLIC_HOST': 'https://vendas.example'},
                          {'VENDA_PUBLIC_HOST': 'vendas.example/path'}):
            result = subprocess.run([str(BINARY)], cwd=ROOT, env={**self.environment, **overrides},
                                    capture_output=True, timeout=5)
            self.assertNotEqual(result.returncode, 0)
            expected = 'Porta inválida' if 'PORT' in overrides else 'O domínio público'
            self.assertIn(expected, result.stderr.decode())


if __name__ == '__main__':
    unittest.main(verbosity=2)
