import { createHash } from 'node:crypto'
import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'

// Politique de sécurité du contenu (OWASP A02 / A05) : seules les ressources de la page, l'API et le
// flux caméra configurés sont autorisés. Les blocs <script>/<style> en ligne d'index.html sont
// autorisés par leur empreinte SHA-256, calculée ici : pas de 'unsafe-inline' pour les scripts.
const sha = (text) => `'sha256-${createHash('sha256').update(text).digest('base64')}'`
const origin = (url) => {
  try {
    return url ? new URL(url).origin : ''
  } catch {
    return ''
  }
}

function csp(env, html = '') {
  const api = origin(env.VITE_API_URL)
  const ws = api.replace(/^http/, 'ws')
  const camera = origin(env.VITE_CAMERA_URL)
  const scripts = [...html.matchAll(/<script>([\s\S]*?)<\/script>/g)].map((m) => sha(m[1]))
  const styles = [...html.matchAll(/<style>([\s\S]*?)<\/style>/g)].map((m) => sha(m[1]))
  return [
    "default-src 'self'",
    `script-src 'self' ${scripts.join(' ')}`.trim(),
    // React applique les styles via le CSSOM, non concerné par la CSP : pas besoin de 'unsafe-inline'
    `style-src 'self' ${styles.join(' ')}`.trim(),
    `img-src 'self' data: ${camera}`.trim(),
    `connect-src 'self' ${api} ${ws} ${camera}`.trim(), // camera : /status de la vision (fraîcheur du flux)
    "font-src 'self'",
    "object-src 'none'",
    "base-uri 'none'",
    "form-action 'self'",
    // frame-ancestors n'a d'effet qu'en en-tête HTTP : il est envoyé par X-Frame-Options (HEADERS)
  ].join('; ')
}

const HEADERS = {
  'X-Content-Type-Options': 'nosniff',
  'X-Frame-Options': 'DENY',
  'Referrer-Policy': 'no-referrer',
  'Permissions-Policy': 'camera=(self), microphone=(), geolocation=()',
}

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), 'VITE_')
  return {
    plugins: [
      react(),
      {
        name: 'fortex-csp',
        // Build : CSP en <meta> (le fichier peut être servi par n'importe quel serveur statique)
        transformIndexHtml: {
          order: 'post',
          handler(html, ctx) {
            if (ctx.server) return html // développement : HMR de Vite incompatible avec une CSP stricte
            return html.replace('<head>', `<head>\n    <meta http-equiv="Content-Security-Policy" content="${csp(env, html)}" />`)
          },
        },
      },
    ],
    // `vite preview` (démo) : en-têtes de sécurité HTTP en plus de la CSP du fichier
    preview: { headers: HEADERS },
    server: { headers: HEADERS },
    build: { sourcemap: false }, // pas de code source exposé en production
  }
})
