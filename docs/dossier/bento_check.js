// Controle d'un deck Bento : liste les anomalies du document et exporte chaque slide en PNG.
//
//   node docs/dossier/bento_check.js <deck.bento.html> [dossier-png]
//
// Ouvre le deck dans Brave, interroge `window.bento.validate()` (debordements de texte,
// elements hors canvas, liens casses, cles de chart non implementees...) puis passe en mode
// presentation et capture les slides une a une. Le rendu est la seule verification qui
// attrape ce que le JSON ne montre pas : une verification sans capture ne vaut rien.

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

function resolveBrowser() {
  const candidates = [
    '/opt/brave.com/brave/brave',
    '/usr/bin/brave-browser',
    '/usr/bin/google-chrome',
    '/usr/bin/chromium',
  ]
  for (const candidate of candidates) if (fs.existsSync(candidate)) return candidate
  return undefined
}

const [, , deckPath, outDir = '/tmp/bento-slides'] = process.argv
if (!deckPath) {
  console.error('usage: node bento_check.js <deck.bento.html> [dossier-png]')
  process.exit(2)
}

const { chromium } = require(resolvePlaywright())

;(async () => {
  fs.mkdirSync(outDir, { recursive: true })
  const browser = await chromium.launch({
    executablePath: resolveBrowser(),
    args: ['--no-sandbox', '--font-render-hinting=none'],
  })
  const page = await browser.newPage({ viewport: { width: 1280, height: 720 } })
  await page.goto('file://' + path.resolve(deckPath), { waitUntil: 'load' })
  await page.waitForFunction(() => !!(window.bento && window.bento.validate), null, { timeout: 30000 })
  await page.waitForTimeout(1500)

  const report = await page.evaluate(() => {
    const v = window.bento.validate()
    return { ok: v.ok, counts: v.counts, findings: v.findings }
  })
  const notable = report.findings.filter((f) => f.severity !== 'info')
  console.log(`validate() ok=${report.ok} findings=${report.findings.length} (severite > info : ${notable.length})`)
  for (const f of notable) {
    console.log(`  ${f.severity.toUpperCase()} ${f.code} slide=${f.slide || '-'} el=${f.element || '-'} :: ${f.message}`)
  }

  // Le bouton « Slideshow » n'est pas actionnable en headless : on retombe sur les vignettes du
  // panneau de gauche, repere par leur rapport 16:9.
  try {
    await page.locator('[aria-label="Slideshow"], button:has-text("Slideshow")').first()
      .click({ timeout: 5000 })
    await page.waitForTimeout(1200)
    const n = await page.evaluate(() => {
      const m = document.body.innerText.match(/(\d+)\s*\/\s*(\d+)/)
      return m ? Number(m[2]) : 0
    })
    if (n > 0) {
      console.log(`slides en presentation : ${n}`)
      for (let i = 1; i <= n; i++) {
        const file = path.join(outDir, `s${String(i).padStart(2, '0')}.png`)
        await page.screenshot({ path: file })
        console.log(`  capture ${file}`)
        await page.keyboard.press('ArrowRight')
        await page.waitForTimeout(700)
      }
      await browser.close()
      return
    }
  } catch (e) { /* plan B */ }

  // Toutes les vignettes doivent etre dans le DOM pour etre cliquees : on agrandit la fenetre.
  await page.setViewportSize({ width: 1440, height: 1900 })
  await page.waitForTimeout(800)
  const boxes = await page.evaluate(() => {
    const nine = (w, h) => Math.abs(w / h - 16 / 9) < 0.04
    const all = [...document.querySelectorAll('div,canvas,img')]
      .map((el) => el.getBoundingClientRect())
      .filter((r) => nine(r.width, r.height) && r.width > 60 && r.height > 30)
    const stage = all.filter((r) => r.x > 220 && r.width > 380)
      .sort((a, b) => b.width * b.height - a.width * a.height)[0]
    const thumbs = all.filter((r) => r.x < 220 && r.width > 80 && r.width < 220)
      .sort((a, b) => (a.y - b.y) || (b.width - a.width))
    const seen = new Set()
    const unique = []
    for (const r of thumbs) {
      const key = Math.round(r.y / 20)
      if (seen.has(key)) continue
      seen.add(key)
      unique.push(r)
    }
    const round = (r) => ({ x: r.x, y: r.y, w: r.width, h: r.height })
    return { stage: stage ? round(stage) : null, thumbs: unique.map(round) }
  })
  if (!boxes.stage) throw new Error('canvas 16:9 introuvable')
  const stage = boxes.stage
  const thumbs = boxes.thumbs
  console.log(`slides detectees : ${thumbs.length}`)
  for (let i = 0; i < thumbs.length; i++) {
    const t = thumbs[i]
    await page.mouse.click(t.x + t.w / 2, t.y + t.h / 2)
    await page.waitForTimeout(700)
    const file = path.join(outDir, `s${String(i + 1).padStart(2, '0')}.png`)
    await page.screenshot({ path: file, clip: { x: stage.x, y: stage.y, width: stage.w, height: stage.h } })
    console.log(`  capture ${file}`)
  }
  await browser.close()
})().catch((error) => {
  console.error('échec du contrôle :', error.message)
  process.exit(1)
})
