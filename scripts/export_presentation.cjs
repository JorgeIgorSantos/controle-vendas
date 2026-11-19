#!/usr/bin/env node
/* Exporta o HTML da apresentação para PDF usando o mesmo layout do navegador. */
const fs = require('node:fs');
const path = require('node:path');
const { pathToFileURL } = require('node:url');

let chromium;
for (const moduleName of [process.env.PLAYWRIGHT_MODULE, '../.tools/browser/package', 'playwright', 'playwright-core'].filter(Boolean)) {
  try { ({ chromium } = require(moduleName)); break; } catch {}
}
if (!chromium) {
  console.error('Instale as ferramentas com python3 scripts/setup-tools.py antes de exportar.');
  process.exit(1);
}

const root = path.resolve(__dirname, '..');
const input = path.resolve(root, process.argv[2] || 'docs/apresentacao.html');
const output = path.resolve(root, process.argv[3] || 'docs/apresentacao.pdf');

async function main() {
  if (!fs.existsSync(input)) throw new Error('Apresentação HTML não encontrada: ' + input);
  fs.mkdirSync(path.dirname(output), { recursive: true });
  const browser = await chromium.launch({
    headless: true,
    executablePath: process.env.CHROME_BIN || '/usr/bin/google-chrome',
    args: ['--no-sandbox', '--disable-dev-shm-usage'],
  });
  try {
    const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
    await page.goto(pathToFileURL(input).href, { waitUntil: 'load' });
    await page.evaluate(async () => {
      await document.fonts.ready;
      await Promise.all(Array.from(document.images, image => image.decode()));
    });
    const slides = await page.locator('.slide').evaluateAll(items => items.map(slide => {
      const title = slide.querySelector('h1,h2').cloneNode(true);
      title.querySelectorAll('br').forEach(line => line.replaceWith(' '));
      return {
        title: title.textContent.replace(/\s+/g, ' ').trim(),
        speaker: slide.querySelector('.slide-notes strong').textContent.trim(),
        notes: slide.querySelector('.slide-notes p').textContent.trim(),
      };
    }));
    await page.emulateMedia({ media: 'print', reducedMotion: 'reduce' });
    await page.pdf({ path: output, printBackground: true, preferCSSPageSize: true, tagged: true });
    const script = [
      'APRESENTAÇÃO DA APLICAÇÃO CONTROLE DE VENDAS',
      'Estácio S.A. Turma 3003. Professora Suzane Alfaia Dias.',
      'Duração sugerida: cerca de 12 minutos, com tempo adicional para demonstração e perguntas.',
      '',
      'COMO APRESENTAR',
      'Abra docs/apresentacao.html no navegador. As imagens e as fontes já estão incorporadas.',
      'Use as setas para navegar, F para tela cheia e N para mostrar ou ocultar as notas.',
      'O PDF contém um slide por página. As notas ficam no HTML e neste roteiro.',
      'As telas usam dados fictícios. O exemplo acompanha duas unidades de café a R$ 24,90.',
      '',
      ...slides.flatMap(slide => [
        slide.title,
        slide.speaker, slide.notes, '',
      ]),
    ].join('\n');
    fs.writeFileSync(path.join(path.dirname(output), 'roteiro-apresentacao.txt'), script.trimEnd() + '\n');
    console.log('PDF gerado: ' + output);
  } finally {
    await browser.close();
  }
}

main().catch(error => { console.error(error.message); process.exitCode = 1; });
