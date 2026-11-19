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

## Hospedagem gratuita no Render

O arquivo `render.yaml` configura um serviço Docker no plano **Free**, com saúde em `/api/health`. No Render, crie um Web Service a partir deste repositório e selecione Docker e Free. A aplicação reconhece automaticamente `PORT` e `RENDER_EXTERNAL_HOSTNAME`.

Essa hospedagem serve para demonstração: o Render suspende o serviço após 15 minutos sem acesso, e os dados do SQLite são perdidos ao suspender, reiniciar ou atualizar o serviço. A primeira visita após a suspensão pode demorar cerca de um minuto. [Limites oficiais do plano gratuito](https://render.com/docs/free).

O site permite cadastrar e alterar os dados de demonstração. O encerramento remoto fica desativado na hospedagem. Para outro domínio HTTPS, configure `VENDA_PUBLIC_HOST` com o domínio sem protocolo, porta ou caminho.

## Executar sem Docker

No Linux ou WSL, use GCC, Make e Node.js 24 LTS (24.15 ou superior) com npm.

```sh
chmod +x iniciar.sh
./iniciar.sh
```

O sistema começa com um banco vazio. Para experimentar com dados fictícios, copie `data/exemplo.db` e indique a cópia com `--db`.

O comando `make` compila o servidor e o Angular. O servidor C entrega a interface e a API no mesmo endereço. O frontend está em `web/src`, com uma rota para cada tela e um serviço HTTP compartilhado.

O backend fica organizado por responsabilidade. `models` reúne a persistência e os auxiliares de consulta; `server` contém o servidor HTTP, o roteador e as validações compartilhadas; `views` separa os handlers da API por funcionalidade. Cadastro e edição de produtos compartilham `salvar_produto.c`.

```text
include/
  app.h                 cabeçalho principal
  models.h              estruturas e acesso ao banco
  http.h                contratos HTTP e utilitários
  views.h               handlers da API
src/
  main.c                inicialização
  models/               banco SQLite e consultas compartilhadas
  server/               HTTP, roteamento e utilitários
  views/
    produtos/           listar, buscar, salvar e excluir
    vendas/             listar, buscar e criar vendas
    sistema/            saúde, encerramento e relatórios
```

## Documentação

- [Instruções completas](README.txt)
- [Requisitos e implementação](docs/requisitos.md)
- [Roteiro da demonstração](docs/roteiro-apresentacao.txt)
- [Banco de demonstração](data/README.txt)
- [Evidências de testes](artifacts/README.txt)
- [Licenças e referências de terceiros](THIRD_PARTY_NOTICES.txt)

A apresentação principal da aplicação está em [PDF](docs/apresentacao.pdf), com 8 slides. O [HTML](docs/apresentacao.html), com navegação e notas para a fala, e o arquivo PowerPoint são versões anteriores. O [relatório técnico](docs/relatorio-tecnico.pdf) descreve a arquitetura, as funcionalidades e os testes da aplicação.

Os arquivos de trabalho, bancos locais e dependências de desenvolvimento não fazem parte do repositório. O banco fictício está em `data/exemplo.db`.
