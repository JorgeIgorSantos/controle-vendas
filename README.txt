VENDA. — SISTEMA DE CONTROLE DE VENDAS EM C
=========================================

INÍCIO RÁPIDO
-------------
Abra o terminal nesta pasta e execute:

  chmod +x iniciar.sh         # necessário após baixar pelo GitHub
  ./iniciar.sh

Abra no navegador:

  http://127.0.0.1:8080

Para encerrar a execução local, use Ctrl+C no terminal.
Os dados permanecem em data/vendas.db. Fechar o navegador não encerra o servidor.
O script sempre muda para a pasta do projeto antes de compilar e executar.

REQUISITOS E COMPILADOR
----------------------
Como alternativa, use Docker Compose conforme a seção abaixo. Nesse modo,
somente Docker e Docker Compose são necessários no computador.

- Linux (ou ambiente Linux no WSL); backend C11/POSIX.
- GCC/cc ou Clang com suporte a C11 e GNU Make.
- Node.js 24 LTS (24.15 ou superior) e npm para compilar a interface Angular.
- Navegador atual com JavaScript e suporte a dialog, fetch e SVG.
- Compilador usado nesta entrega: consultar artifacts/environment.txt.
- SQLite e cJSON já estão incluídos em vendor, com licenças e referências.
- Na primeira compilação local, o Make instala os pacotes do frontend com npm ci.
- Bibliotecas de ligação do ambiente Linux: libc, libm, pthread e dl.
- Python 3 só é necessário para os testes e para gerar o pacote.

DOCKER COMPOSE — COMPILAR E SUBIR TUDO
------------------------------------
Execute nesta pasta:

  docker compose up --build -d --wait

Abra http://127.0.0.1:8080. O build compila o backend em C e a interface
Angular. A imagem final contém o executável, a interface e o SQLite incorporado.
No computador, basta ter Docker e Docker Compose.
O contêiner executa como usuário sem privilégios e tem verificação de saúde.

Se a porta 8080 estiver ocupada, escolha outra:

  PORT=8081 docker compose up --build -d --wait

Nesse caso, abra http://127.0.0.1:8081 e use o mesmo PORT nos demais comandos.
A porta interna acompanha a publicada para preservar as validações de Host e
Origin da aplicação. A publicação fica limitada a 127.0.0.1 no computador.

  docker compose ps            # estado e saúde
  docker compose logs -f app   # acompanhar logs; Ctrl+C sai dos logs
  docker compose stop         # parar
  docker compose up -d --wait  # iniciar novamente
  docker compose down         # remover contêiner e rede, preservando o banco

O SQLite fica em /app/data/vendas.db, no volume nomeado vendas_dados do projeto
controle-vendas. Esse volume persiste ao recriar o contêiner ou executar down.
Não use down -v se quiser preservar os dados: essa opção remove o volume.
O banco do Docker é separado do arquivo data/vendas.db usado fora do contêiner.
Um volume novo começa vazio. Volumes existentes recuperam os dados da loja.
Para parar o contêiner, use docker compose stop; use up -d para iniciar
novamente.

COMPILAÇÃO E EXECUÇÃO MANUAL
---------------------------
  make
  ./build/vendas

  ./build/vendas --port 8081  # usar outra porta
  ./build/vendas --help      # todas as opções

O banco é criado automaticamente. Execute o binário a partir desta pasta.
Para usar um caminho diferente, crie antes a pasta de destino:

  ./build/vendas --db data/minha-loja.db --port 8081

Usar outra porta também altera o endereço no navegador.
Por padrão, o servidor atende somente 127.0.0.1, para uso local. O parâmetro
--host 0.0.0.0 é usado dentro do contêiner para receber o encaminhamento Docker.

FUNCIONALIDADES
---------------
Produtos: cadastrar, listar, pesquisar, editar e excluir. Informe código, nome,
categoria, preço e estoque. Produtos com histórico podem ser desativados.
Vendas: escolha produtos, quantidades e forma de pagamento. O servidor calcula
o total, baixa o estoque e guarda a venda no histórico.
Relatórios: escolha o período para consultar o total e a quantidade de vendas
concluídas.

REGRAS
------
- O código/SKU é único, sem distinguir maiúsculas e minúsculas ASCII.
- IDs internos são gerados automaticamente pelo banco e não são reutilizados.
- Preço é positivo; quantidades são inteiras; estoque não pode ser negativo.
- Produto inativo ou sem quantidade suficiente não pode ser vendido.
- Todos os valores persistidos e calculados no backend usam centavos inteiros.
- Preços e nomes são copiados para os itens da venda, preservando o histórico.
- Venda com vários itens é gravada integralmente ou não é gravada.
- Produtos com histórico de vendas não podem ser excluídos: devem ser desativados.
- Ajustar o estoque na edição significa informar o saldo atual absoluto.
- Limites: preço unitário até R$ 1.000.000,00; estoque até 1.000.000;
  até 200 produtos distintos por venda; total bruto até R$ 90.000.000.000,00.
- Tamanhos de textos são limitados em bytes UTF-8 no backend (código 40, nome
  120, categoria 60 e cliente 120). Acentos podem ocupar mais de um byte.
- Datas são persistidas em UTC; filtros e exibição usam Belém (UTC-3).
- O histórico inclui descontos e cancelamentos registrados em versões anteriores.
  Os totais do relatório somam somente as vendas concluídas.

TESTES E EVIDÊNCIAS
------------------
  make test      # testes de integração da API, executável C e SQLite
  make sanitize  # mesmos testes com ASan/UBSan nos módulos próprios em C

Os testes usam bancos isolados em tests/.runtime, sem alterar o banco da loja.
Os resultados e capturas da versão atual são gravados em artifacts/qa/.
Os arquivos na raiz de artifacts/ registram a versão anterior.

Para repetir os testes de navegador, instale as ferramentas em .tools:

  python3 scripts/setup-tools.py
  node tests/test_ui.cjs

O teste de navegador procura /usr/bin/google-chrome. Use CHROME_BIN para informar
outro executável Chromium.

ESTRUTURA
---------
src/                main.c, http.c, api.c, database.c e utils.c
include/app.h       structs, constantes e contratos dos módulos C
vendor/             SQLite e cJSON com fontes originais
web/src/            rotas, componentes, formulários e serviço HTTP em Angular
data/               arquivo SQLite de trabalho e exemplo.db
tests/              integração HTTP/banco e automação do navegador
docs/               relatório PDF, slides PPTX/PDF, roteiro e requisitos
artifacts/          resultados dos testes, capturas e exportações
scripts/            geração de documentos e pacote de entrega
Dockerfile          compilação C e Angular em etapas separadas
compose.yaml        aplicação, porta local, saúde e volume persistente

O servidor HTTP, o acesso ao banco, as validações e as regras de negócio estão
implementados em C, em arquivos .c e .h. O Angular gera a interface em
web/dist/browser. O servidor C entrega esses arquivos e a API no mesmo endereço.

DOCUMENTAÇÃO E ENTREGA
---------------------
docs/relatorio-tecnico.pdf          Relatório acadêmico da versão anterior
docs/apresentacao.pptx              Slides editáveis da versão anterior
docs/apresentacao.pdf               Slides em PDF da versão anterior
docs/roteiro-apresentacao.txt       Roteiro de 15 min + perguntas
docs/requisitos.md                  Correspondência com cada item do PDF
docs/equipe.json                    Identificação, nomes completos e matrículas

Instituição, professora, turma e os seis nomes informados já estão preenchidos.
Os campos de curso e cidade estão em docs/equipe.json.
O PDF prevê cinco integrantes; confirmar com a professora a equipe de seis.
Foi usada formatação acadêmica base; o modelo institucional não foi fornecido.
Revisar a identificação e a adequação ao modelo da faculdade antes da submissão.
O apêndice oferece divisão sugerida, sem inventar contribuições já realizadas.

  make package

Gera artifacts/entrega-controle-vendas.zip com fontes, bibliotecas, interface,
documentação, testes, instruções, dados de exemplo e evidências.
Não inclui .tools, bancos de teste, objetos intermediários ou banco real da loja.

BACKUP E RECUPERAÇÃO
-------------------
Encerre o servidor antes de copiar data/vendas.db para evitar cópia incompleta
enquanto o SQLite estiver usando WAL. Guarde o backup dentro de data/.
Restaure o arquivo com o servidor encerrado. make clean não apaga o banco.
O arquivo data/exemplo.db contém 8 produtos e 6 vendas fictícias.
Para abrir uma cópia de trabalho do exemplo:

  cp data/exemplo.db data/demonstracao.db
  ./build/vendas --db data/demonstracao.db --port 8081

LIMITES DO ESCOPO ACADÊMICO
--------------------------
Uso local, um servidor com processamento sequencial; sem login, emissão fiscal,
multiusuário remoto, controle de custos ou cálculo de lucro. O frontend e o
backend não dependem de internet durante o uso.
Fontes de terceiros e assistência utilizada: THIRD_PARTY_NOTICES.txt.

EQUIPE
------
Rodrigo de Sousa Barbosa — Matrícula: 202403618168
Manoel de Sousa Santos — Matrícula: 202402239521
Lucas Robert Lopes Silva — Matrícula: 201902231597
Alan Freitas Miranda — Matrícula: 202404621073
Gabriel Henrique Maciel Leite — Matrícula: 202403628988
Jorge Igor Dos Santos Pinto — Matrícula: 202309399989
