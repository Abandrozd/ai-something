import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// The built page is same-origin scripts and stylesheets. React does not need
// eval, and react-markdown renders elements rather than raw HTML, so the
// policy has neither unsafe-eval nor unsafe-inline. Vite's dev server injects
// an inline React refresh preamble, so the policy is applied to the build
// (meta tag) and the preview server (header), not to `vite dev`.
const contentSecurityPolicy = [
  "default-src 'self'",
  "script-src 'self'",
  "style-src 'self'",
  "img-src 'self'",
  "font-src 'self'",
  "connect-src 'self'",
  "object-src 'none'",
  "base-uri 'self'",
  "form-action 'self'",
].join('; ')

// frame-ancestors is ignored inside a meta tag, so only the response header
// carries it. The meta tag is what a static host still enforces.
const contentSecurityPolicyHeader = `${contentSecurityPolicy}; frame-ancestors 'none'`

function contentSecurityPolicyPlugin() {
  const meta = `<meta http-equiv="Content-Security-Policy" content="${contentSecurityPolicy}" />`
  return {
    name: 'content-security-policy',
    apply: 'build',
    transformIndexHtml(html) {
      return html.replace('<head>', `<head>\n    ${meta}`)
    },
  }
}

// Same-origin /api keeps the session cookie first-party, so SameSite=lax is
// sent on fetch. The browser page stays on the Vite origin.
const apiProxyTarget = process.env.VITE_API_PROXY || 'http://127.0.0.1:8000'

const proxy = {
  '/api': {
    target: apiProxyTarget,
    changeOrigin: true,
    rewrite: (path) => path.replace(/^\/api/, ''),
    configure: (proxyServer) => {
      proxyServer.on('proxyRes', (proxyRes) => {
        const location = proxyRes.headers.location
        if (typeof location === 'string' && location.startsWith(apiProxyTarget)) {
          proxyRes.headers.location = `/api${location.slice(apiProxyTarget.length)}`
        }
      })
    },
  },
}

// https://vite.dev/config/
export default defineConfig({
  plugins: [react(), contentSecurityPolicyPlugin()],
  server: { proxy },
  preview: {
    proxy,
    headers: {
      'Content-Security-Policy': contentSecurityPolicyHeader,
    },
  },
})
