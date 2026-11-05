# Conferência do PDF — Sistema de controle de vendas

Fonte: `Projeto_Pratico_C_4_Pontos.pdf`, 4 páginas, lidas integralmente. A aplicação é em C11, dividida em `.c` e `.h`, e oferece interface gráfica no navegador. Os arquivos de interface usam as linguagens do navegador. Não há dependência de C++.

| Requisito obrigatório | Implementação | Evidência |
|---|---|---|
| 1. Menu organizado, retorno e encerramento | Navegação Visão geral/Produtos/Vendas/Relatórios; botões Voltar, modais, Ctrl+C no terminal ou docker compose stop | `web/index.html`, `web/app.js`, teste API 18 e testes UI |
| 2. Struct com cinco campos e identificador | `Product` contém ID, SKU, nome, categoria, preço, estoque, mínimo, situação e notas; `Sale` e `SaleItem` | `include/app.h` |
| 3. Cadastrar, listar, pesquisar, atualizar e excluir | CRUD completo de produtos; SKU único e ID automático | `src/api.c`; testes API 02 e 03; testes UI de CRUD |
| 4. Pelo menos duas regras específicas | Venda com baixa de estoque, total e desconto; cancelamento com reposição; relatório agregado | testes API 05 a 09, 13 e 16 |
| 5. Condicionais e laços | validações `if`, menus via rotas, processamento de itens com `for`, servidor com `while` | `src/api.c`, `src/http.c` |
| 6. Funções com responsabilidades definidas | servidor, persistência, regras, conversões e inicialização separados | `src/*.c` |
| 7. Ponteiros e memória dinâmica | `SaleItem *items` com `calloc`; buffers com `malloc/calloc`; verificações e `free` em sucesso/falha | `src/api.c`, `src/http.c`; `make sanitize` |
| 8. Salvar e recuperar arquivos | SQLite em `data/vendas.db` com transações, WAL e integridade referencial | teste API 11, reinício real e `PRAGMA integrity_check` |
| 9. Validar entradas e IDs repetidos | campos obrigatórios, limites, tipos, SKU duplicado, datas, quantidades, pagamento, descontos e estoque | testes API 03, 04, 07, 09, 10 e 12; captura 05 |
| 10. Separação `.c` / `.h` e comentários | cinco módulos C, cabeçalho de contratos e estruturas, comentários de decisões relevantes | `src/`, `include/` |
| Interface gráfica indispensável | Interface responsiva com formulários, tabelas, gráficos SVG e modais | 9 testes UI; capturas desktop e celular |

## Planejamento

Problema: organizar o cadastro de produtos e registrar vendas com cálculos corretos, evitando estoques negativos e perda de informações. Público: pequenos estabelecimentos e demonstração acadêmica. Entradas: produtos e itens de venda. Saídas: catálogo, histórico, comprovantes, indicadores, CSV e impressão.

```mermaid
flowchart TD
  A[Iniciar executável C] --> B[Abrir ou criar arquivo SQLite]
  B --> C[Abrir interface gráfica]
  C --> D{Menu principal}
  D --> E[CRUD de produtos]
  D --> F[Registrar e consultar vendas]
  D --> G[Consultar relatórios]
  E --> D
  F --> D
  G --> D
  D --> H[Encerrar servidor e preservar banco]
```

```mermaid
flowchart TD
  A[Selecionar itens e pagamento] --> B[Validar tipos e quantidades em C]
  B --> C[BEGIN IMMEDIATE]
  C --> D[Ler preços e estoques atuais]
  D --> E{Estoque e desconto válidos?}
  E -- Não --> F[ROLLBACK e mensagem]
  E -- Sim --> G[Inserir venda e cópias dos itens]
  G --> H[Atualizar estoques]
  H --> I[COMMIT e comprovante]
```

## Entregas e organização

| Entrega do enunciado | Arquivo |
|---|---|
| Fontes e software | `src/`, `include/`, `vendor/`, `web/`, `Makefile`, `iniciar.sh` |
| Relatório técnico em PDF | `docs/relatorio-tecnico.pdf` |
| Slides | `docs/apresentacao.pptx` e `docs/apresentacao.pdf` |
| README.txt | `README.txt` na raiz |
| Dados de exemplo | `data/exemplo.db` e opção `--demo` |
| Casos de teste e evidências | `tests/`, JSON e PNG em `artifacts/` e tabelas no relatório |
| Pasta compactada | `artifacts/entrega-controle-vendas.zip` |

O relatório inclui capa com identificação única da equipe, sumário com páginas, introdução, objetivos, requisitos, desenvolvimento, estruturas, fluxograma, funções, testes com resultados reais, manual, conclusão, referências e apêndice. Identificação recebida: Estácio S.A, turma 3003, professora Suzane Alfaia Dias; Rodrigo de Sousa Barbosa, Manoel de Sousa Santos, Lucas Robert Lopes Silva, Alan Freitas Miranda, Gabriel Henrique Maciel Leite e Jorge Igor Dos Santos Pinto. Curso e cidade permanecem campos a preencher em `docs/equipe.json`, pois não foram fornecidos. A divisão da equipe é uma proposta para validação; a participação real não é presumida. O PDF prevê cinco integrantes, mas foram informados seis: os seis nomes foram preservados, cabendo confirmar a composição com a professora.

O roteiro prevê 15 minutos de exposição, 5 de perguntas, participação dos seis integrantes informados, uma entrada inválida, recuperação após reiniciar e explicação de código. A avaliação individual exige que cada integrante compreenda a solução.

### Identificação dos integrantes

| Nome | Matrícula |
| --- | --- |
| Rodrigo de Sousa Barbosa | 202403618168 |
| Manoel de Sousa Santos | 202402239521 |
| Lucas Robert Lopes Silva | 201902231597 |
| Alan Freitas Miranda | 202404621073 |
| Gabriel Henrique Maciel Leite | 202403628988 |
| Jorge Igor Dos Santos Pinto | 202309399989 |
