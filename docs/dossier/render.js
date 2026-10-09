// Rend un HTML du dossier (docs/dossier/) en PDF avec Chromium/Brave.
//
//   node docs/dossier/render.js <html> <sortie.pdf> [chemin-du-navigateur]
//
// Le dossier est en A4 et le poster en A3 portrait : les deux documents sont rendus
// separement, en respectant la regle @page de chacun.
//
// Playwright est résolu depuis node_modules du projet s'il existe, sinon depuis le cache `npx`.
// Brave est utilisé par défaut : aucune distribution Chromium n'est installée sur ce poste.

const fs = require('node:fs')
const path = require('node:path')

function resolvePlaywright() {
  const local = path.join(__dirname, '..', '..', 'dev', 'dashboard', 'node_modules', 'playwright')
  if (fs.existsSync(local)) return local
  const cache = path.join(process.env.HOME || '', '.npm', '_npx')
  for (const entry of fs.existsSync(cache) ? fs.readdirSync(cache) : []) {
    const candidate = path.join(cache, entry, 'node_modules', 'playwright')
    if (fs.existsSync(candidate)) return candidate
  }
  throw new Error('Playwright introuvable : npm i -D playwright (ou npx playwright)')
}

function resolveBrowser(explicit) {
  const candidates = [
    explicit,
    '/opt/brave.com/brave/brave',
    '/usr/bin/brave-browser',
    '/usr/bin/google-chrome',
    '/usr/bin/chromium',
  ].filter(Boolean)
  for (const candidate of candidates) if (fs.existsSync(candidate)) return candidate
  return undefined // laisse Playwright choisir son navigateur par défaut
}

const [, , htmlPath, outPath, browserPath] = process.argv
if (!htmlPath || !outPath) {
  console.error('usage: node render.js <html> <sortie.pdf> [navigateur]')
  process.exit(2)
}

const { chromium } = require(resolvePlaywright())

;(async () => {
  const browser = await chromium.launch({
    executablePath: resolveBrowser(browserPath),
    args: ['--no-sandbox', '--font-render-hinting=none'],
  })
  const page = await browser.newPage()
  await page.goto('file://' + path.resolve(htmlPath), { waitUntil: 'load' })
  await page.emulateMedia({ media: 'print' })
  await page.evaluate(() => document.fonts && document.fonts.ready)
  await page.pdf({
    path: outPath,
    preferCSSPageSize: true, // respecte @page (dossier A4, poster A3 portrait)
    printBackground: true,
    displayHeaderFooter: false,
  })
  const { size } = fs.statSync(outPath)
  console.log(`PDF : ${outPath} (${Math.round(size / 1024)} Ko)`)
  await browser.close()
})().catch((error) => {
  console.error('échec du rendu :', error.message)
  process.exit(1)
})
