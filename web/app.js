'use strict';

const paths = {
  dashboard: '<rect x="3" y="3" width="7" height="7" rx="1.5"/><rect x="14" y="3" width="7" height="7" rx="1.5"/><rect x="3" y="14" width="7" height="7" rx="1.5"/><rect x="14" y="14" width="7" height="7" rx="1.5"/>',
  box: '<path d="m12 3 9 5-9 5-9-5 9-5Z"/><path d="M3 8v9l9 5 9-5V8M12 13v9M7.5 5.5l9 5"/>',
  bag: '<path d="M5 7h14l1 14H4L5 7Z"/><path d="M8 8V6a4 4 0 0 1 8 0v2"/>',
  chart: '<path d="M4 3v17h17M8 15v-4M13 15V7M18 15V4"/>',
  plus: '<path d="M12 5v14M5 12h14"/>',
  arrow: '<path d="M5 12h14m-5-5 5 5-5 5"/>',
  trend: '<path d="m3 17 6-6 4 4 8-10M15 5h6v6"/>',
  search: '<circle cx="10.5" cy="10.5" r="6.5"/><path d="m16 16 5 5"/>',
  edit: '<path d="m15 5 4 4M4 20l4-1L20 7a2.8 2.8 0 0 0-4-4L4 15l-1 6Z"/>',
  trash: '<path d="M3 6h18M9 6V3h6v3M5 6l1 15h12l1-15M10 10v7M14 10v7"/>',
  close: '<path d="m6 6 12 12M6 18 18 6"/>',
  eye: '<path d="M2 12s4-7 10-7 10 7 10 7-4 7-10 7S2 12 2 12Z"/><circle cx="12" cy="12" r="3"/>',
  wallet: '<rect x="3" y="5" width="18" height="15" rx="3"/><path d="M3 8V5a2 2 0 0 1 2-2h12M16 11h5v5h-5a2.5 2.5 0 0 1 0-5Z"/>',
  ticket: '<path d="M4 4h16v5a3 3 0 0 0 0 6v5H4v-5a3 3 0 0 0 0-6V4ZM13 5v2m0 3v3m0 3v3"/>',
  calendar: '<rect x="3" y="5" width="18" height="16" rx="2"/><path d="M7 3v4m10-4v4M3 11h18"/>',
  download: '<path d="M12 3v12m-5-5 5 5 5-5M4 16v5h16v-5"/>',
  print: '<path d="M7 8V3h10v5M7 17H3V9h18v8h-4M7 14h10v7H7Z"/><path d="M17 11h1"/>',
  alert: '<path d="M10 4 2 18a2 2 0 0 0 2 3h16a2 2 0 0 0 2-3L14 4a2.3 2.3 0 0 0-4 0Z"/><path d="M12 9v4m0 3v1"/>',
  spark: '<path d="m12 3 2.5 6.5L21 12l-6.5 2.5L12 21l-2.5-6.5L3 12l6.5-2.5L12 3ZM20 2v4m-2-2h4"/>',
  card: '<rect x="2" y="4" width="20" height="16" rx="3"/><path d="M2 9h20M6 15h4"/>',
  check: '<path d="m5 12 4 4L19 6"/>',
  refresh: '<path d="M20 7v5h-5M4 17v-5h5M5.5 7a8 8 0 0 1 13-2L20 7M4 17l1.5 2a8 8 0 0 0 13-2"/>',
};
const icon = (name, size = 18) => `<svg width="${size}" height="${size}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.65" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${paths[name] || paths.box}</svg>`;
const $ = selector => document.querySelector(selector);
const h = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const money = cents => new Intl.NumberFormat('pt-BR', {style:'currency', currency:'BRL'}).format((Number(cents) || 0) / 100);
const number = value => new Intl.NumberFormat('pt-BR').format(value || 0);
const paymentNames = {pix:'Pix', dinheiro:'Dinheiro', credito:'Cartão de crédito', debito:'Cartão de débito'};
const pageNames = {dashboard:'Visão geral', products:'Produtos', sales:'Vendas', reports:'Relatórios'};
const colors = ['','sage','blue','lilac','gold'];
const state = {page:'dashboard', days:7, products:[], productSearch:'', productStatus:'all', productCategory:'', productStock:'all', salesSearch:'', salesFrom:'', salesTo:'', reportFrom:'', reportTo:'', report:null, cart:new Map(), saleProducts:[], catalogSearch:'', renderToken:0};

function todayISO() {
  const parts = new Intl.DateTimeFormat('en-US', {timeZone:'America/Belem', year:'numeric', month:'2-digit', day:'2-digit'}).formatToParts(new Date());
  const find = type => parts.find(x => x.type === type).value;
  return `${find('year')}-${find('month')}-${find('day')}`;
}
function addDays(day, amount) { const date = new Date(`${day}T12:00:00Z`); date.setUTCDate(date.getUTCDate() + amount); return date.toISOString().slice(0,10); }
function shortDate(day) { const [y,m,d] = day.split('-'); return `${d}/${m}/${y}`; }
function dateTime(iso) { return new Intl.DateTimeFormat('pt-BR', {dateStyle:'short',timeStyle:'short',timeZone:'America/Belem'}).format(new Date(iso)); }
function normalize(text) { return String(text).normalize('NFD').replace(/[\u0300-\u036f]/g,'').toLowerCase(); }
function moneyInput(cents) { return (cents / 100).toFixed(2).replace('.',','); }
function parseMoney(value, allowZero = true) {
  const clean = String(value).trim();
  if (!/^\d{1,13}([,.]\d{1,2})?$/.test(clean)) throw new Error('Informe o valor com até duas casas decimais, por exemplo: 24,90.');
  const [whole, fraction = ''] = clean.replace(',','.').split('.');
  const cents = Number(whole) * 100 + Number(fraction.padEnd(2,'0'));
  if (!Number.isSafeInteger(cents) || (!allowZero && cents <= 0)) throw new Error('O preço deve ser maior que zero.');
  return cents;
}
async function api(path, options = {}) {
  try {
    const response = await fetch(path, {cache:'no-store', ...options, headers:{'Content-Type':'application/json', ...options.headers}});
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || 'Não foi possível concluir a operação.');
    return data;
  } catch (error) {
    if (error instanceof TypeError) {
      throw new Error('Não foi possível carregar os dados. Verifique a conexão e tente novamente.');
    }
    throw error;
  }
}
function toast(message, error = false) {
  const item = document.createElement('div');
  item.className = `toast${error ? ' error' : ''}`;
  item.textContent = message;
  $('#toasts').append(item);
  setTimeout(() => item.remove(), 6000);
}
function emptyState(title, text, action = '', compact = false) {
  return `<div class="empty-state ${compact ? 'compact' : ''}">${icon('box',32)}<h3>${h(title)}</h3><p>${h(text)}</p>${action}</div>`;
}
function newSaleButton() { return `<button class="button primary" data-action="new-sale">${icon('plus',16)}Nova venda</button>`; }
function pageHeading(eyebrow, title, subtitle, action = '', extraClass = '') {
  return `<div class="page-heading ${extraClass}"><div><h1>${title}</h1><p>${subtitle}</p></div>${action}</div>`;
}
function stat(label, value, name, caption, featured = false) {
  return `<article class="stat-card ${featured ? 'featured' : ''}"><div class="stat-top"><span>${label}</span></div><div class="stat-value">${value}</div><div class="stat-caption">${caption}</div></article>`;
}
function statGrid(summary, report = false) {
  return `<div class="stats-grid">${stat('Total vendido',money(summary.total_cents),'wallet','Vendas concluídas no período',true)}${stat('Vendas realizadas',number(summary.sale_count),'bag',`${number(summary.items_sold)} unidades vendidas`)}${stat('Ticket médio',money(summary.average_cents),'ticket','Valor médio por venda')}${report ? stat('Descontos concedidos',money(summary.discount_cents),'spark',`${number(summary.cancelled_count)} vendas canceladas no período`) : stat('Produtos ativos',number(summary.active_products),'box',`<b>${number(summary.low_stock_count)} com estoque baixo</b>`)}</div>`;
}
function revenueChart(report, from, to) {
  const daily = new Map(report.daily.map(x => [x.day,x.total_cents]));
  const dayCount = Math.round((new Date(`${to}T12:00:00Z`) - new Date(`${from}T12:00:00Z`)) / 86400000) + 1;
  let data = [];
  if (dayCount <= 93) { for (let i = 0; i < dayCount; i++) { const day = addDays(from,i); data.push({day,total_cents:daily.get(day) || 0}); } }
  else data = report.daily.length ? report.daily : [{day:from,total_cents:0},{day:to,total_cents:0}];
  if (!data.length) data = [{day:from,total_cents:0}];
  const left = 53, right = 604, top = 17, bottom = 167;
  const max = Math.max(...data.map(x => x.total_cents),10000) * 1.2;
  const x = i => data.length === 1 ? (left+right)/2 : left + i/(data.length-1)*(right-left);
  const y = value => bottom - value/max*(bottom-top);
  const points = data.map((value,i) => `${x(i).toFixed(1)},${y(value.total_cents).toFixed(1)}`).join(' ');
  let grid = '';
  for (let i = 0; i < 4; i++) { const value = max*i/3, yy = y(value); grid += `<line class="chart-grid" x1="${left}" y1="${yy}" x2="${right}" y2="${yy}"/><text class="chart-label" x="${left-12}" y="${yy+3}" text-anchor="end">${h(new Intl.NumberFormat('pt-BR',{maximumFractionDigits:0,notation:'compact'}).format(value/100))}</text>`; }
  const labels = [...new Set(Array.from({length:Math.min(7,data.length)},(_,i) => Math.round(i*(data.length-1)/Math.max(Math.min(7,data.length)-1,1))))];
  const names = labels.map(i => `<text class="chart-label" x="${x(i)}" y="194" text-anchor="middle">${h(data[i].day.slice(8,10)+'/'+data[i].day.slice(5,7))}</text>`).join('');
  const circles = data.length <= 31 ? data.map((d,i) => `<circle class="chart-point" cx="${x(i)}" cy="${y(d.total_cents)}" r="${d.total_cents ? 3 : 0}"><title>${shortDate(d.day)}: ${money(d.total_cents)}</title></circle>`).join('') : '';
  return `<div class="chart-container"><svg class="revenue-chart" viewBox="0 0 628 207" role="img" aria-label="Total vendido por dia, de ${shortDate(from)} a ${shortDate(to)}"><defs><linearGradient id="revenue-gradient" x1="0" x2="0" y1="0" y2="1"><stop offset="0%" stop-color="#ed663f" stop-opacity=".17"/><stop offset="100%" stop-color="#ed663f" stop-opacity=".01"/></linearGradient></defs>${grid}<polygon class="chart-area" points="${x(0)},${bottom} ${points} ${x(data.length-1)},${bottom}"/><polyline class="chart-line" points="${points}"/>${circles}${names}</svg></div>`;
}
function topProducts(report) {
  return report.top_products.length ? `<div class="top-products">${report.top_products.slice(0,4).map((p,i) => `<div class="top-product"><div class="top-product-info"><strong title="${h(p.name)}">${h(p.name)}</strong><small>${h(p.sku)}</small></div><div class="top-product-value">${number(p.quantity)} un.<small>${money(p.gross_cents)}</small></div></div>`).join('')}</div>` : emptyState('Nenhum produto vendido','Os produtos vendidos no período aparecerão aqui.','',true);
}
function saleRows(sales) {
  return sales.map(s => `<tr><td><span class="sale-id">#${String(s.id).padStart(4,'0')}</span></td><td><strong>${h(s.customer || 'Cliente balcão')}</strong></td><td>${h(dateTime(s.created_at))}</td><td>${h(paymentNames[s.payment_method])}</td><td class="right"><strong>${money(s.total_cents)}</strong></td><td><span class="badge ${s.status === 'cancelled' ? 'cancelled' : ''}">${s.status === 'cancelled' ? 'Cancelada' : 'Concluída'}</span></td><td class="right"><button class="icon-button" data-action="sale-detail" data-id="${s.id}" title="Ver venda #${s.id}" aria-label="Ver venda #${s.id}">${icon('eye',16)}</button></td></tr>`).join('');
}
function salesTable(sales) {
  return sales.length ? `<div class="table-wrap"><table><thead><tr><th>Venda</th><th>Cliente</th><th>Data e hora</th><th>Pagamento</th><th class="right">Total</th><th>Situação</th><th aria-label="Ações"></th></tr></thead><tbody>${saleRows(sales)}</tbody></table></div>` : emptyState('Nenhuma venda encontrada','Registre uma venda ou ajuste o período da consulta.',newSaleButton());
}
async function renderDashboard(token) {
  const to = todayISO(), from = addDays(to,-state.days+1);
  const report = await api(`/api/reports?${new URLSearchParams({from,to})}`);
  if (token !== state.renderToken) return;
  $('#view').innerHTML = pageHeading('','Visão geral','Vendas e estoque no período selecionado.',newSaleButton()) +
    `<div class="section-toolbar"><div class="section-label">Resumo da loja <span>• ${shortDate(from).slice(0,5)} a ${shortDate(to).slice(0,5)}</span></div><div class="segments" aria-label="Período do resumo">${[1,7,30].map(d => `<button data-action="period" data-days="${d}" class="${state.days===d?'selected':''}" aria-pressed="${state.days===d}">${d===1?'Hoje':d+' dias'}</button>`).join('')}</div></div>` + statGrid(report.summary) +
    (report.summary.low_stock_count ? `<div class="alert-strip">${icon('alert',16)}<span>${number(report.summary.low_stock_count)} produtos precisam de atenção no estoque.</span><a href="#products" data-action="low-stock">Ver produtos ${icon('arrow',12)}</a></div>` : '') +
    `<div class="dashboard-grid"><section class="panel"><div class="panel-header"><div><h2>Vendas por dia</h2></div><span class="chart-legend"><i></i>Total vendido</span></div>${revenueChart(report,from,to)}<div class="chart-footer"><span>Valores em reais (R$)</span><strong>${number(report.summary.sale_count)} vendas no período</strong></div></section><section class="panel"><div class="panel-header"><div><h2>Produtos mais vendidos</h2></div></div>${topProducts(report)}<a href="#reports" class="panel-link">Ver relatório ${icon('arrow',12)}</a></section></div>` +
    `<section class="panel table-panel"><div class="panel-header"><div><h2>Últimas vendas</h2></div><a href="#sales" class="button small">Ver todas ${icon('arrow',12)}</a></div>${salesTable(report.sales.slice(0,5))}<div class="table-footer"><span>${report.sales.length ? `Exibindo ${Math.min(5,report.sales.length)} de ${number(report.sales.length)} vendas no período` : 'Nenhuma venda no período.'}</span></div></section>`;
}

async function renderProducts(token) {
  const products = await api('/api/products');
  if (token !== state.renderToken) return;
  state.products = products;
  const categories = [...new Set(products.map(p => p.category))].sort((a,b)=>a.localeCompare(b,'pt-BR'));
  $('#view').innerHTML = pageHeading('','Produtos','Cadastro e controle de estoque.',`<button class="button primary" data-action="new-product">${icon('plus',16)}Novo produto</button>`) +
    `<section class="panel"><div class="filter-bar"><div class="search-box">${icon('search',16)}<input type="search" id="product-search" placeholder="Buscar por nome, código ou categoria…" aria-label="Buscar produtos" value="${h(state.productSearch)}"></div><select id="product-category" aria-label="Filtrar categoria"><option value="">Todas as categorias</option>${categories.map(c => `<option value="${h(c)}" ${c===state.productCategory?'selected':''}>${h(c)}</option>`).join('')}</select><select id="product-status" aria-label="Filtrar situação"><option value="all">Todos os produtos</option><option value="active">Ativos</option><option value="inactive">Inativos</option></select><select id="product-stock" aria-label="Filtrar estoque"><option value="all">Todo o estoque</option><option value="low">Estoque baixo</option></select></div><div id="products-results"></div></section><div class="inventory-summary"><span>${icon('box',14)}<strong>${number(products.length)}</strong> produtos cadastrados</span><span><strong>${number(products.filter(p=>p.active).length)}</strong> ativos</span></div>`;
  $('#product-status').value = state.productStatus;
  $('#product-stock').value = state.productStock;
  drawProducts();
}
function drawProducts() {
  const q = normalize(state.productSearch);
  const products = state.products.filter(p => (!q || normalize(`${p.sku} ${p.name} ${p.category}`).includes(q)) && (!state.productCategory || p.category === state.productCategory) && (state.productStatus === 'all' || Boolean(p.active) === (state.productStatus === 'active')) && (state.productStock !== 'low' || (p.active && p.stock <= p.min_stock)));
  $('#products-results').innerHTML = products.length ? `<div class="table-wrap"><table><thead><tr><th>Produto</th><th>Categoria</th><th class="right">Preço unitário</th><th>Estoque</th><th>Situação</th><th class="right">Ações</th></tr></thead><tbody>${products.map((p,i) => `<tr><td><div class="product-cell"><div><strong>${h(p.name)}</strong><small>${h(p.sku)}</small></div></div></td><td>${h(p.category)}</td><td class="right"><strong>${money(p.price_cents)}</strong></td><td><span class="stock-number">${number(p.stock)} un.</span><span class="stock-note">Mínimo: ${number(p.min_stock)}</span></td><td><span class="badge ${!p.active?'cancelled':p.stock===0?'empty':p.stock<=p.min_stock?'low':''}">${!p.active?'Inativo':p.stock===0?'Sem estoque':p.stock<=p.min_stock?'Estoque baixo':'Disponível'}</span></td><td><div class="actions"><button class="icon-button" data-action="edit-product" data-id="${p.id}" title="Editar ${h(p.name)}" aria-label="Editar ${h(p.name)}">${icon('edit',16)}</button><button class="icon-button danger" data-action="delete-product" data-id="${p.id}" title="Excluir ${h(p.name)}" aria-label="Excluir ${h(p.name)}">${icon('trash',16)}</button></div></td></tr>`).join('')}</tbody></table></div><div class="table-footer"><span>${number(products.length)} produtos encontrados</span><span>Preços em reais (R$)</span></div>` : emptyState(state.products.length?'Nenhum produto encontrado':'Nenhum produto cadastrado','Cadastre um produto ou ajuste os filtros para continuar.',`<button class="button primary" data-action="new-product">${icon('plus',15)}Cadastrar produto</button>`);
}

function datesForm(from,to,type) {
  return `<form class="date-filter" id="${type}-dates"><label for="${type}-from">De</label><input type="date" id="${type}-from" name="from" value="${from}" min="1900-01-01" max="9999-12-31" required aria-label="Data inicial"><label for="${type}-to">até</label><input type="date" id="${type}-to" name="to" value="${to}" min="1900-01-01" max="9999-12-31" required aria-label="Data final"><button class="button small" type="submit">Aplicar</button></form>`;
}
async function renderSales(token) {
  if (!state.salesFrom) { state.salesTo=todayISO(); state.salesFrom=addDays(state.salesTo,-29); }
  const sales = await api(`/api/sales?${new URLSearchParams({from:state.salesFrom,to:state.salesTo,search:state.salesSearch})}`);
  if (token !== state.renderToken) return;
  $('#view').innerHTML = pageHeading('','Vendas','Histórico e detalhes das vendas.',newSaleButton()) +
    `<section class="panel"><div class="filter-bar"><form class="search-box" id="sales-search-form">${icon('search',16)}<input type="search" name="search" id="sales-search" placeholder="Cliente ou número da venda…" aria-label="Buscar vendas" value="${h(state.salesSearch)}"></form>${datesForm(state.salesFrom,state.salesTo,'sales')}</div>${salesTable(sales)}<div class="table-footer"><span>${number(sales.length)} vendas encontradas</span><span>Concluídas: <strong>${money(sales.filter(s=>s.status==='completed').reduce((sum,s)=>sum+s.total_cents,0))}</strong></span></div></section>`;
}
async function renderReports(token) {
  if (!state.reportFrom) { state.reportTo=todayISO(); state.reportFrom=addDays(state.reportTo,-29); }
  const report = await api(`/api/reports?${new URLSearchParams({from:state.reportFrom,to:state.reportTo})}`);
  if (token !== state.renderToken) return;
  state.report = report;
  $('#view').innerHTML = pageHeading('RESULTADOS','Relatórios','Totais de vendas, produtos e formas de pagamento.',`<div class="heading-actions"><button class="button" data-action="export-csv">${icon('download',15)}Exportar CSV</button> <button class="button primary" data-action="print">${icon('print',15)}Imprimir</button></div>`,'report-heading') +
    `<div class="section-toolbar"><span class="section-label">Relatório de vendas</span>${datesForm(state.reportFrom,state.reportTo,'report')}</div><div class="period-banner">${icon('calendar',16)}<span>Período de <strong>${shortDate(state.reportFrom)}</strong> a <strong>${shortDate(state.reportTo)}</strong>. Totais consideram apenas vendas concluídas. Horário de Belém (UTC−3).</span></div>` + statGrid(report.summary,true) +
    `<div class="report-grid"><section class="panel"><div class="panel-header"><div><h2>Evolução das vendas</h2><p>Total líquido por dia, após os descontos</p></div><span class="chart-legend"><i></i>Total vendido</span></div>${revenueChart(report,state.reportFrom,state.reportTo)}<div class="chart-footer"><span>Faturamento bruto: <strong>${money(report.summary.subtotal_cents)}</strong></span><span>Descontos: <strong>${money(report.summary.discount_cents)}</strong></span></div></section><section class="panel"><div class="panel-header"><div><h2>Formas de pagamento</h2><p>Distribuição por forma de pagamento</p></div></div><div class="payments">${report.payments.length?report.payments.map(p=>`<div class="payment-row"><span>${icon(p.payment_method==='pix'?'spark':p.payment_method==='dinheiro'?'wallet':'card',17)}</span><div><strong>${h(paymentNames[p.payment_method])}</strong><small>${number(p.sale_count)} vendas · ${report.summary.total_cents?Math.round(p.total_cents/report.summary.total_cents*100):0}% do total</small></div><b>${money(p.total_cents)}</b></div>`).join(''):'<div class="cart-empty">Nenhum pagamento no período.</div>'}<div class="summary-total"><span>Total vendido</span><strong>${money(report.summary.total_cents)}</strong></div></div></section></div>` +
    `<section class="panel table-panel"><div class="panel-header"><div><h2>Produtos mais vendidos</h2><p>Os 10 destaques do período em unidades</p></div><span class="count-tag">${number(report.summary.items_sold)} unidades</span></div>${report.top_products.length?`<div class="table-wrap"><table><thead><tr><th>Posição</th><th>Produto</th><th>Código</th><th class="right">Unidades</th><th class="right">Receita bruta</th></tr></thead><tbody>${report.top_products.map((p,i)=>`<tr><td>${String(i+1).padStart(2,'0')}</td><td><strong>${h(p.name)}</strong></td><td>${h(p.sku)}</td><td class="right">${number(p.quantity)}</td><td class="right"><strong>${money(p.gross_cents)}</strong></td></tr>`).join('')}</tbody></table></div>`:emptyState('Ainda sem dados neste período','Ajuste as datas ou registre sua primeira venda.','',true)}<p class="report-note">A receita bruta dos produtos é calculada antes dos descontos, que são aplicados ao total da venda. Vendas canceladas permanecem no histórico e são excluídas dos totais.</p></section>`;
}

async function renderPage() {
  const page = location.hash.slice(1);
  state.page = Object.hasOwn(pageNames,page) ? page : 'dashboard';
  const token = ++state.renderToken;
  document.querySelectorAll('[data-page]').forEach(link=>{link.classList.toggle('active',link.dataset.page===state.page);if(link.dataset.page===state.page)link.setAttribute('aria-current','page');else link.removeAttribute('aria-current');});
  $('#breadcrumb').textContent=pageNames[state.page];
  document.title = `${pageNames[state.page]} — Venda.`;
  $('#view').innerHTML='<div class="loading">Carregando…</div>';
  try { await ({dashboard:renderDashboard,products:renderProducts,sales:renderSales,reports:renderReports}[state.page])(token); }
  catch(error) { if(token===state.renderToken) $('#view').innerHTML=`<div class="error-panel"><h2>Não foi possível carregar os dados</h2><p>${h(error.message)}</p><button class="button" data-action="reload">${icon('refresh',15)}Tentar novamente</button></div>`; }
}
function modalHeader(title,subtitle) {return `<div class="modal-header"><div><h2 id="modal-title">${title}</h2><p>${subtitle}</p></div><button type="button" class="icon-button" data-action="close-modal" aria-label="Fechar janela">${icon('close',20)}</button></div>`;}
function openModal(html,className='') { const modal=$('#modal');modal.className=className;modal.innerHTML=html;if(!modal.open)modal.showModal(); }
function formError(form,message) {const el=form.querySelector('.form-error');el.textContent=message;el.classList.add('visible');el.setAttribute('role','alert');el.scrollIntoView({block:'nearest'});}
function askConfirm(title,text,button='Confirmar',danger=true) {
  return new Promise(resolve=>{
    const dialog=$('#confirm-modal');
    dialog.innerHTML=`<div class="modal-body"><h2 id="confirm-title">${h(title)}</h2><p>${h(text)}</p></div><div class="modal-footer"><button class="button" value="cancel" autofocus>Voltar</button><button class="button ${danger?'danger':'primary'}" value="confirm">${h(button)}</button></div>`;
    dialog.returnValue='cancel';
    const click = event => {const b=event.target.closest('button');if(b)dialog.close(b.value);};
    dialog.addEventListener('click',click);
    dialog.addEventListener('close',()=>{dialog.removeEventListener('click',click);resolve(dialog.returnValue==='confirm');},{once:true});
    dialog.showModal();
  });
}
async function productModal(id=0) {
  const p = id ? await api(`/api/products/${id}`) : {sku:'',name:'',category:'',price_cents:0,stock:0,min_stock:5,active:1,notes:''};
  openModal(`${modalHeader(id?'Editar produto':'Novo produto',id?'Atualize as informações do seu catálogo.':'Informe os dados do produto.')}<form id="product-form" data-id="${id}"><div class="modal-body"><div class="form-error"></div><div class="form-grid"><div class="form-field"><label for="p-sku">Código do produto <span>*</span></label><input id="p-sku" name="sku" required maxlength="40" placeholder="Ex.: CAF-001" value="${h(p.sku)}"><small>Código único no catálogo.</small></div><div class="form-field"><label for="p-category">Categoria <span>*</span></label><input id="p-category" name="category" required maxlength="60" list="categories" placeholder="Ex.: Mercearia" value="${h(p.category)}"><datalist id="categories">${['Mercearia','Casa e decoração','Papelaria','Utilidades','Acessórios','Outros'].map(c=>`<option value="${c}"></option>`).join('')}</datalist></div><div class="form-field full"><label for="p-name">Nome do produto <span>*</span></label><input id="p-name" name="name" required maxlength="120" placeholder="Ex.: Café especial 250 g" value="${h(p.name)}"></div><div class="form-field"><label for="p-price">Preço de venda (R$) <span>*</span></label><input id="p-price" name="price" inputmode="decimal" required maxlength="12" placeholder="0,00" value="${id?moneyInput(p.price_cents):''}"><small>Use até duas casas decimais. Máximo R$ 1.000.000.</small></div><div class="form-field"><label for="p-stock">Quantidade em estoque <span>*</span></label><input type="number" id="p-stock" name="stock" required min="0" max="1000000" step="1" value="${p.stock}"></div><div class="form-field"><label for="p-min">Estoque mínimo <span>*</span></label><input type="number" id="p-min" name="min_stock" required min="0" max="1000000" step="1" value="${p.min_stock}"><small>Um alerta aparece ao atingir este valor.</small></div><div class="form-field"><label>Situação</label><label class="checkbox-field"><input type="checkbox" name="active" ${p.active?'checked':''}>Produto ativo para venda</label></div><div class="form-field full"><label for="p-notes">Observações</label><textarea id="p-notes" name="notes" maxlength="500" placeholder="Informações adicionais (opcional)">${h(p.notes)}</textarea></div></div></div><div class="modal-footer"><button type="button" class="button" data-action="close-modal">Voltar</button><button type="submit" class="button primary">${icon('check',15)}${id?'Salvar alterações':'Cadastrar produto'}</button></div></form>`);
}

async function openSale() {
  state.saleProducts=await api('/api/products?status=active');state.cart=new Map();state.catalogSearch='';
  openModal(`${modalHeader('Nova venda','Escolha os produtos, confira os valores e finalize.')}<form id="sale-form"><div class="sale-layout"><section class="sale-catalog"><div class="search-box">${icon('search',16)}<input type="search" id="catalog-search" placeholder="Buscar produto ou código…" aria-label="Buscar produtos para a venda"></div><div class="sale-product-list" id="sale-product-list"></div></section><section class="sale-cart"><div class="cart-title"><h3>Itens da venda</h3><span class="count-tag" id="cart-count">0 itens</span></div><div class="form-error"></div><div class="cart-items" id="cart-items"></div><div class="form-grid"><div class="form-field full"><label for="s-customer">Cliente</label><input name="customer" id="s-customer" maxlength="120" placeholder="Cliente balcão (opcional)"></div><div class="form-field"><label for="s-payment">Forma de pagamento <span>*</span></label><select id="s-payment" name="payment_method" required>${Object.entries(paymentNames).map(([key,value])=>`<option value="${key}">${value}</option>`).join('')}</select></div><div class="form-field"><label for="s-discount">Desconto (R$)</label><input id="s-discount" name="discount" inputmode="decimal" value="0,00" placeholder="0,00"></div><div class="form-field full"><label for="s-notes">Observações</label><textarea id="s-notes" name="notes" maxlength="500" placeholder="Observações (opcional)"></textarea></div></div><div class="sale-totals"><div><span>Subtotal</span><strong id="cart-subtotal">${money(0)}</strong></div><div><span>Desconto</span><span id="cart-discount">${money(0)}</span></div><div class="grand-total"><span>Total da venda</span><strong id="cart-total">${money(0)}</strong></div></div></section></div><div class="modal-footer"><small>O estoque será atualizado ao concluir a venda.</small><div><button type="button" class="button" data-action="close-modal">Voltar</button><button type="submit" class="button primary" id="finish-sale">${icon('check',15)}Finalizar venda</button></div></div></form>`,'sale-dialog');
  drawCatalog();drawCart();
}
function drawCatalog() {
  const q=normalize(state.catalogSearch),products=state.saleProducts.filter(p=>normalize(`${p.name} ${p.sku} ${p.category}`).includes(q));
  $('#sale-product-list').innerHTML=products.length?products.map((p,i)=>`<button type="button" class="catalog-product" data-action="cart-add" data-id="${p.id}" ${p.stock===0?'disabled':''} aria-label="Adicionar ${h(p.name)}"><span class="catalog-info"><strong>${h(p.name)}</strong><small>${h(p.sku)} · ${p.stock===0?'Sem estoque':number(p.stock)+' un. disponíveis'}</small></span><b>${money(p.price_cents)}</b><span class="catalog-plus">+</span></button>`).join(''):emptyState('Nenhum produto disponível','Cadastre um produto ativo ou ajuste a busca.','',true);
}
function drawCart() {
  $('#cart-count').textContent=`${[...state.cart.values()].reduce((n,i)=>n+i.quantity,0)} itens`;
  $('#cart-items').innerHTML=state.cart.size?[...state.cart.values()].map(item=>`<div class="cart-line"><div class="cart-line-info"><strong>${h(item.product.name)}</strong><small>${money(item.product.price_cents)} / un.</small></div><div class="quantity-controls"><button type="button" data-action="cart-less" data-id="${item.product.id}" aria-label="Diminuir ${h(item.product.name)}">−</button><input type="number" min="1" max="${item.product.stock}" step="1" value="${item.quantity}" data-quantity="${item.product.id}" aria-label="Quantidade de ${h(item.product.name)}"><button type="button" data-action="cart-add" data-id="${item.product.id}" aria-label="Aumentar ${h(item.product.name)}">+</button></div><b>${money(item.quantity*item.product.price_cents)}</b><button type="button" class="icon-button danger" data-action="cart-remove" data-id="${item.product.id}" aria-label="Remover ${h(item.product.name)}">${icon('close',14)}</button></div>`).join(''):'<div class="cart-empty">Nenhum item adicionado.</div>';
  drawTotals();
}
function drawTotals() {
  const subtotal=[...state.cart.values()].reduce((n,i)=>n+i.quantity*i.product.price_cents,0);
  let discount=0;try{discount=parseMoney($('#s-discount').value||'0');}catch{/* A mensagem de validação é exibida ao finalizar. */}
  $('#cart-subtotal').textContent=money(subtotal);$('#cart-discount').textContent=`− ${money(discount)}`;$('#cart-total').textContent=money(Math.max(0,subtotal-discount));
  $('#finish-sale').disabled=!state.cart.size;
}
function changeCart(id,delta) {
  const p=state.saleProducts.find(p=>p.id===id);if(!p)return;
  const quantity=(state.cart.get(id)?.quantity||0)+delta;
  if(quantity>p.stock) {toast('A quantidade não pode superar o estoque disponível.',true);return;}
  if(quantity<=0)state.cart.delete(id);else state.cart.set(id,{product:p,quantity});drawCart();
}
async function saleDetail(id) {
  const sale=await api(`/api/sales/${id}`);
  openModal(`${modalHeader(`Venda #${String(id).padStart(4,'0')}`,`${h(dateTime(sale.created_at))} · Horário de Belém`)}<div class="modal-body"><div class="detail-meta"><div><small>Cliente</small><strong>${h(sale.customer||'Cliente balcão')}</strong></div><div><small>Pagamento</small><strong>${h(paymentNames[sale.payment_method])}</strong></div><div><small>Situação</small><span class="badge ${sale.status==='cancelled'?'cancelled':''}">${sale.status==='cancelled'?'Cancelada':'Concluída'}</span></div><div><small>${sale.cancelled_at?'Cancelada em':'Itens vendidos'}</small><strong>${sale.cancelled_at?h(dateTime(sale.cancelled_at)):number(sale.items.reduce((n,i)=>n+i.quantity,0))+' unidades'}</strong></div></div><div class="table-wrap receipt-table"><table><thead><tr><th>Produto</th><th class="right">Qtd.</th><th class="right">Unitário</th><th class="right">Total</th></tr></thead><tbody>${sale.items.map(i=>`<tr><td><strong>${h(i.name)}</strong><span class="stock-note">${h(i.sku)}</span></td><td class="right">${number(i.quantity)}</td><td class="right">${money(i.unit_price_cents)}</td><td class="right"><strong>${money(i.total_cents)}</strong></td></tr>`).join('')}</tbody></table></div><div class="sale-totals"><div><span>Subtotal</span><span>${money(sale.subtotal_cents)}</span></div><div><span>Desconto</span><span>− ${money(sale.discount_cents)}</span></div><div class="grand-total"><span>Total da venda</span><strong>${money(sale.total_cents)}</strong></div></div>${sale.notes?`<p class="receipt-notes">${h(sale.notes)}</p>`:''}<p class="report-note">Comprovante de controle interno. Não é um documento fiscal.</p></div><div class="modal-footer">${sale.status==='completed'?`<button class="button" data-action="cancel-sale" data-id="${id}">Cancelar venda</button>`:''}<button class="button" data-action="print">${icon('print',15)}Imprimir</button><button class="button primary" data-action="close-modal">Concluir</button></div>`);
}
function exportCSV() {
  const report=state.report;if(!report)return;
  const cell=value=>{let text=String(value??'');if(/^[=+\-@\t\r\n]/.test(text))text="'"+text;return '"'+text.replaceAll('"','""')+'"';};
  const rows=[['Venda','Data e hora (Belém)','Cliente','Pagamento','Situação','Subtotal (R$)','Desconto (R$)','Total (R$)','Unidades'],...report.sales.map(s=>[s.id,dateTime(s.created_at),s.customer||'Cliente balcão',paymentNames[s.payment_method],s.status==='completed'?'Concluída':'Cancelada',moneyInput(s.subtotal_cents),moneyInput(s.discount_cents),moneyInput(s.total_cents),s.item_count]),[],['Resumo (somente concluídas)'],['Período',shortDate(state.reportFrom)+' a '+shortDate(state.reportTo)],['Total vendido (R$)',moneyInput(report.summary.total_cents)],['Vendas realizadas',report.summary.sale_count],['Unidades vendidas',report.summary.items_sold]];
  const blob=new Blob(['\ufeff'+rows.map(row=>row.map(cell).join(';')).join('\r\n')],{type:'text/csv;charset=utf-8'});
  const url=URL.createObjectURL(blob),link=document.createElement('a');link.href=url;link.download=`vendas_${state.reportFrom}_${state.reportTo}.csv`;document.body.append(link);link.click();link.remove();setTimeout(()=>URL.revokeObjectURL(url),1000);toast('Relatório CSV exportado.');
}

document.addEventListener('click',async event=>{
  const button=event.target.closest('[data-action]');if(!button)return;
  const action=button.dataset.action,id=Number(button.dataset.id);
  try {
    if(action==='new-product')await productModal();
    else if(action==='edit-product')await productModal(id);
    else if(action==='delete-product'){
      const p=state.products.find(p=>p.id===id);
      if(await askConfirm('Excluir este produto?',`${p?.name||'O produto'} será removido do catálogo. Produtos com vendas no histórico devem ser desativados.`,'Excluir produto')){await api(`/api/products/${id}`,{method:'DELETE'});toast('Produto excluído.');await renderPage();}
    } else if(action==='new-sale')await openSale();
    else if(action==='close-modal'){
      if($('#sale-form')&&state.cart.size&&!(await askConfirm('Sair desta venda?','Os itens selecionados serão descartados. Nenhuma venda foi registrada.','Descartar venda')))return;
      $('#modal').close();
    } else if(action==='period'){state.days=Number(button.dataset.days);await renderPage();}
    else if(action==='low-stock'){state.productStock='low';if(state.page==='products')await renderPage();}
    else if(action==='cart-add')changeCart(id,1);
    else if(action==='cart-less')changeCart(id,-1);
    else if(action==='cart-remove'){state.cart.delete(id);drawCart();}
    else if(action==='sale-detail')await saleDetail(id);
    else if(action==='cancel-sale'){
      if(await askConfirm('Cancelar esta venda?','Os produtos serão devolvidos ao estoque. A venda continuará no histórico, mas será removida dos totais.','Cancelar venda')){
        button.disabled=true;await api(`/api/sales/${id}/cancel`,{method:'POST',body:'{}'});toast('Venda cancelada e estoque devolvido.');await saleDetail(id);await renderPage();
      }
    } else if(action==='export-csv')exportCSV();
    else if(action==='print')window.print();
    else if(action==='reload')await renderPage();

  } catch(error){button.disabled=false;toast(error.message,true);}
});
document.addEventListener('input',event=>{
  const el=event.target;
  if(el.id==='product-search'){state.productSearch=el.value;drawProducts();}
  else if(el.id==='catalog-search'){state.catalogSearch=el.value;drawCatalog();}
  else if(el.id==='s-discount')drawTotals();
});
document.addEventListener('change',event=>{
  const el=event.target;
  if(el.id==='product-category'){state.productCategory=el.value;drawProducts();}
  else if(el.id==='product-status'){state.productStatus=el.value;drawProducts();}
  else if(el.id==='product-stock'){state.productStock=el.value;drawProducts();}
  else if(el.dataset.quantity){
    const id=Number(el.dataset.quantity),item=state.cart.get(id),quantity=Number(el.value);
    if(!Number.isInteger(quantity)||quantity<1||quantity>item.product.stock){toast('Use uma quantidade inteira entre 1 e o estoque disponível.',true);el.value=item.quantity;return;}
    item.quantity=quantity;drawCart();
  }
});
document.addEventListener('submit',async event=>{
  const form=event.target;
  if(!['product-form','sale-form','sales-dates','report-dates','sales-search-form'].includes(form.id))return;
  event.preventDefault();const fields=new FormData(form),button=form.querySelector('[type=submit]');
  if(button)button.disabled=true;
  try {
    if(form.id==='product-form'){
      const data={sku:fields.get('sku').trim(),name:fields.get('name').trim(),category:fields.get('category').trim(),price_cents:parseMoney(fields.get('price'),false),stock:Number(fields.get('stock')),min_stock:Number(fields.get('min_stock')),active:fields.get('active')==='on',notes:fields.get('notes').trim()};
      if(data.price_cents>100000000)throw new Error('O preço máximo permitido é R$ 1.000.000,00.');
      const id=Number(form.dataset.id);await api(`/api/products${id?'/'+id:''}`,{method:id?'PUT':'POST',body:JSON.stringify(data)});$('#modal').close();toast(id?'Produto atualizado.':'Produto cadastrado.');await renderPage();
    } else if(form.id==='sale-form'){
      if(!state.cart.size)throw new Error('Adicione pelo menos um produto.');
      const data={customer:fields.get('customer').trim(),payment_method:fields.get('payment_method'),discount_cents:parseMoney(fields.get('discount')||'0'),notes:fields.get('notes').trim(),items:[...state.cart.values()].map(i=>({product_id:i.product.id,quantity:i.quantity}))};
      const subtotal=[...state.cart.values()].reduce((n,i)=>n+i.quantity*i.product.price_cents,0);
      if(data.discount_cents>subtotal)throw new Error('O desconto não pode ser maior que o subtotal.');
      const sale=await api('/api/sales',{method:'POST',body:JSON.stringify(data)});state.cart.clear();toast(`Venda #${String(sale.id).padStart(4,'0')} registrada. Total: ${money(sale.total_cents)}`);await saleDetail(sale.id);await renderPage();
    } else if(form.id==='sales-dates'||form.id==='report-dates'){
      const from=fields.get('from'),to=fields.get('to');if(from>to)throw new Error('A data inicial deve ser anterior ou igual à data final.');
      if(form.id==='sales-dates'){state.salesFrom=from;state.salesTo=to;}else{state.reportFrom=from;state.reportTo=to;}
      await renderPage();
    } else if(form.id==='sales-search-form'){state.salesSearch=fields.get('search').trim();await renderPage();}
  } catch(error){if(form.querySelector('.form-error'))formError(form,error.message);else toast(error.message,true);}
  finally{if(button?.isConnected)button.disabled=false;}
});
$('#modal').addEventListener('cancel',event=>{if($('#sale-form')&&state.cart.size){event.preventDefault();askConfirm('Sair desta venda?','Os itens selecionados serão descartados. Nenhuma venda foi registrada.','Descartar venda').then(ok=>{if(ok)$('#modal').close();});}});
document.querySelectorAll('[data-icon]').forEach(el=>{el.outerHTML=icon(el.dataset.icon,18);});
$('#current-date').textContent=new Intl.DateTimeFormat('pt-BR',{day:'numeric',month:'long',year:'numeric',timeZone:'America/Belem'}).format(new Date());
window.addEventListener('hashchange',renderPage);
renderPage();
