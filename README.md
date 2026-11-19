# Controle de vendas

Controle de vendas com frontend Angular, servidor C11 e banco SQLite. O menu tem três telas: Produtos, Vendas e Relatórios.

## Executar com Docker

```sh
git clone https://github.com/JorgeIgorSantos/controle-vendas.git
cd controle-vendas
docker compose up --build -d --wait
```

Acesse [http://localhost:8080](http://localhost:8080).

Para parar: `docker compose stop`. Os dados ficam em um volume persistente.

## Executar sem Docker

No Linux ou WSL, use GCC, Make e Node.js 24 LTS (24.15 ou superior) com npm.

```sh
chmod +x iniciar.sh
./iniciar.sh
```

O sistema começa com um banco vazio. Para experimentar com dados fictícios, copie `data/exemplo.db` e indique a cópia com `--db`.

O comando `make` compila o servidor e o Angular. O servidor C entrega a interface e a API no mesmo endereço. O frontend está em `web/src`, com uma rota para cada tela e um serviço HTTP compartilhado.

O backend separa as funcionalidades em `src/products.c` (produtos), `src/sales.c` (vendas e estoque) e `src/reports.c` (relatórios). O `src/api.c` encaminha as rotas para esses módulos; `src/api_helpers.c` reúne as conversões de consultas para JSON e os filtros compartilhados. Os contratos de cada módulo ficam nos respectivos cabeçalhos em `include/`.

## Documentação

- [Instruções completas](README.txt)
- [Requisitos e implementação](docs/requisitos.md)
- [Roteiro da demonstração](docs/roteiro-apresentacao.txt)
- [Banco de demonstração](data/README.txt)
- [Evidências de testes](artifacts/README.txt)
- [Licenças e referências de terceiros](THIRD_PARTY_NOTICES.txt)

A apresentação da aplicação está disponível em [HTML](docs/apresentacao.html), com navegação e notas para a fala, e em [PDF](docs/apresentacao.pdf). O [relatório técnico](docs/relatorio-tecnico.pdf) descreve a arquitetura, as funcionalidades e os testes da versão atual. O arquivo PowerPoint é uma referência da versão anterior.

Os arquivos de trabalho, bancos locais e dependências de desenvolvimento não fazem parte do repositório. O banco fictício está em `data/exemplo.db`.
