# Controle de vendas

Aplicação em C11 com interface web, SQLite e execução com Docker.

## Executar com Docker

```sh
git clone https://github.com/JorgeIgorSantos/controle-vendas.git
cd controle-vendas
docker compose up --build -d --wait
```

Acesse [http://localhost:8080](http://localhost:8080).

Para parar: `docker compose stop`. Os dados ficam em um volume persistente.

## Executar sem Docker

No Linux ou WSL, com GCC e Make instalados:

```sh
chmod +x iniciar.sh
./iniciar.sh
```

Para incluir dados fictícios em um banco vazio: `./iniciar.sh --demo`.

## Documentação

- [Instruções completas](README.txt)
- [Relatório técnico](docs/relatorio-tecnico.pdf)
- [Apresentação em PDF](docs/apresentacao.pdf)
- [Relatório de vendas de exemplo](artifacts/relatorio-vendas-exemplo.pdf)
- [Licenças e referências de terceiros](THIRD_PARTY_NOTICES.txt)

Os arquivos de trabalho, bancos locais e dependências de desenvolvimento não fazem parte do repositório. O banco fictício está em `data/exemplo.db`.
