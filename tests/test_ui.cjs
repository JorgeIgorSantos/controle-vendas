/* Teste real no Chrome. Instale playwright-core em .tools ou use scripts/setup-tools.sh. */
const fs = require('node:fs');
const path = require('node:path');
const assert = require('node:assert/strict');
const {spawn} = require('node:child_process');
const root = path.resolve(__dirname,'..');
let chromium;
try { ({chromium} = require('../.tools/browser/package')); }
catch { ({chromium} = require('../.tools/node_modules/playwright-core')); }
process.env.TMPDIR = path.join(root,'.tools','tmp');
fs.mkdirSync(process.env.TMPDIR,{recursive:true});
const db = path.join(root,'tests','.runtime','ui.db');
for(const suffix of ['','-wal','-shm']) fs.rmSync(db+suffix,{force:true});
const port=18091, base=`http://127.0.0.1:${port}`;
const server=spawn(path.join(root,'build','vendas'),['--port',String(port),'--db',db,'--demo'],{cwd:root,stdio:['ignore','pipe','pipe']});
let serverLog='';server.stdout.on('data',x=>serverLog+=x);server.stderr.on('data',x=>serverLog+=x);
const results=[];
let browser;
async function check(name,fn){await fn();results.push({test:name,result:'APROVADO'});console.log('OK',name);}
async function waitServer(){for(let i=0;i<100;i++){try{if((await fetch(base+'/api/health')).ok)return;}catch{}await new Promise(r=>setTimeout(r,50));}throw new Error('Servidor indisponível: '+serverLog);}
async function fillProduct(page,sku,name='Produto de teste UI'){
  await page.getByRole('button',{name:'Novo produto',exact:true}).click();
  await page.locator('#p-sku').fill(sku);await page.locator('#p-name').fill(name);await page.locator('#p-category').fill('Testes');await page.locator('#p-price').fill('19,90');await page.locator('#p-stock').fill('5');await page.locator('#p-min').fill('1');
  await page.getByRole('button',{name:'Cadastrar produto',exact:true}).click();
}
async function main(){
  await waitServer();
  browser=await chromium.launch({headless:true,executablePath:process.env.CHROME_BIN||'/usr/bin/google-chrome',args:['--no-sandbox','--disable-dev-shm-usage']});
  const context=await browser.newContext({viewport:{width:1440,height:1000},locale:'pt-BR',timezoneId:'America/Belem',acceptDownloads:true});
  const page=await context.newPage(),errors=[];
  page.on('pageerror',error=>errors.push(error.message));
  await check('Dashboard com dados reais do SQLite',async()=>{
    await page.goto(base);await page.getByRole('heading',{name:'Visão geral'}).waitFor();
    assert.equal(await page.locator('.stat-value').first().textContent(),'R$ 495,90');
    assert.equal(await page.locator('nav a').count(),4);
    await page.locator('#toasts').evaluate(el=>el.replaceChildren());await page.screenshot({path:path.join(root,'artifacts','01-visao-geral.png'),fullPage:true});
  });
  await check('Cadastro pelo formulário atualiza o catálogo',async()=>{
    await page.getByRole('link',{name:'Produtos',exact:true}).click();await page.getByRole('heading',{name:'Produtos'}).waitFor();
    await fillProduct(page,'UI-001');await page.locator('#modal').waitFor({state:'hidden'});
    await page.locator('#product-search').fill('UI-001');await page.getByRole('cell').filter({hasText:'Produto de teste UI'}).waitFor();
  });
  await check('Código duplicado exibe erro visível e mantém formulário',async()=>{
    await fillProduct(page,'UI-001','Duplicado');await page.locator('.form-error.visible').waitFor();assert.match(await page.locator('.form-error').textContent(),/código único/);
    await page.locator('#toasts').evaluate(el=>el.replaceChildren());await page.screenshot({path:path.join(root,'artifacts','05-validacao.png'),fullPage:true});await page.getByRole('button',{name:'Fechar janela'}).click();
  });
  await check('Edição do preço e exclusão confirmada pelo navegador',async()=>{
    await page.getByRole('button',{name:'Editar Produto de teste UI',exact:true}).click();await page.locator('#p-price').fill('21,90');await page.getByRole('button',{name:'Salvar alterações'}).click();await page.locator('#modal').waitFor({state:'hidden'});
    await page.locator('#product-search').fill('');await fillProduct(page,'UI-DELETE','Produto para excluir');await page.locator('#modal').waitFor({state:'hidden'});await page.locator('#product-search').fill('UI-DELETE');
    await page.getByRole('button',{name:'Excluir Produto para excluir',exact:true}).click();await page.locator('#confirm-modal').getByRole('button',{name:'Excluir produto',exact:true}).click();await page.getByRole('heading',{name:'Nenhum produto encontrado'}).waitFor();
    await page.locator('#product-search').fill('');await page.locator('#toasts').evaluate(el=>el.replaceChildren());await page.screenshot({path:path.join(root,'artifacts','02-produtos.png'),fullPage:true});
  });
  await check('Carrinho calcula venda e backend baixa estoque',async()=>{
    await page.getByRole('link',{name:'Vendas',exact:true}).click();await page.getByRole('heading',{name:'Vendas'}).waitFor();await page.getByRole('button',{name:'Nova venda',exact:true}).click();await page.locator('#catalog-search').fill('UI-001');
    await page.getByRole('button',{name:'Adicionar Produto de teste UI',exact:true}).click();await page.getByRole('button',{name:'Adicionar Produto de teste UI',exact:true}).click();
    await page.locator('#s-customer').fill('Cliente da interface');await page.locator('#s-discount').fill('1,80');assert.equal(await page.locator('#cart-total').textContent(),'R$ 42,00');
    await page.locator('#toasts').evaluate(el=>el.replaceChildren());await page.screenshot({path:path.join(root,'artifacts','03-nova-venda.png'),fullPage:true});await page.getByRole('button',{name:'Finalizar venda'}).click();await page.getByRole('heading',{name:'Venda #0007',exact:true}).waitFor();
    assert.equal(await page.locator('.grand-total strong').textContent(),'R$ 42,00');await page.getByRole('button',{name:'Concluir',exact:true}).click();
    const products=await (await fetch(base+'/api/products')).json();assert.equal(products.find(p=>p.sku==='UI-001').stock,3);
  });
  await check('Detalhe e cancelamento devolvem estoque e preservam histórico',async()=>{
    await page.getByRole('button',{name:'Ver venda #7',exact:true}).click();await page.getByRole('heading',{name:'Venda #0007',exact:true}).waitFor();
    await page.locator('#toasts').evaluate(el=>el.replaceChildren());await page.screenshot({path:path.join(root,'artifacts','06-comprovante.png'),fullPage:true});
    await page.getByRole('button',{name:'Cancelar venda',exact:true}).click();await page.locator('#confirm-modal').getByRole('button',{name:'Cancelar venda',exact:true}).click();await page.locator('#modal .badge.cancelled').waitFor();await page.getByRole('button',{name:'Concluir',exact:true}).click();
    const products=await (await fetch(base+'/api/products')).json();assert.equal(products.find(p=>p.sku==='UI-001').stock,5);
    assert.equal((await (await fetch(base+'/api/sales/7')).json()).status,'cancelled');
  });
  await check('Relatório exporta CSV com total correto e gera impressão PDF',async()=>{
    await page.getByRole('link',{name:'Relatórios',exact:true}).click();await page.getByRole('heading',{name:'Relatórios'}).waitFor();
    assert.equal(await page.locator('.stat-value').first().textContent(),'R$ 495,90');
    const downloadPromise=page.waitForEvent('download');await page.getByRole('button',{name:'Exportar CSV',exact:true}).click();const download=await downloadPromise;const target=path.join(root,'artifacts','relatorio-exemplo.csv');await download.saveAs(target);assert.match(fs.readFileSync(target,'utf8'),/495,90/);
    await page.locator('#toasts').evaluate(el=>el.replaceChildren());await page.screenshot({path:path.join(root,'artifacts','04-relatorios.png'),fullPage:true});await page.pdf({path:path.join(root,'artifacts','relatorio-vendas-exemplo.pdf'),format:'A4',printBackground:true,margin:{top:'12mm',bottom:'12mm',left:'10mm',right:'10mm'}});
  });
  await check('Layout em celular sem transbordamento horizontal',async()=>{
    await page.setViewportSize({width:390,height:844});await page.getByRole('link',{name:'Visão geral',exact:true}).click();await page.getByRole('heading',{name:'Visão geral'}).waitFor();
    assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth),true);
    await page.locator('#toasts').evaluate(el=>el.replaceChildren());await page.screenshot({path:path.join(root,'artifacts','07-celular.png'),fullPage:true});
  });
  await check('Nenhum erro JavaScript durante os fluxos',async()=>assert.deepEqual(errors,[]));
  await browser.close();browser=null;
}
main().then(()=>{fs.writeFileSync(path.join(root,'artifacts','ui-test-results.json'),JSON.stringify({executed_at:new Date().toISOString(),command:'node tests/test_ui.cjs',total:results.length,tests:results},null,2));}).catch(async error=>{console.error(error);process.exitCode=1;if(browser)await browser.close();}).finally(()=>{server.kill('SIGTERM');});
