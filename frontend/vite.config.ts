import { defineConfig, type ProxyOptions } from 'vite'
import react from '@vitejs/plugin-react'

const backendTarget = process.env.VITE_BACKEND_URL ?? 'http://localhost:8000'

// Several backend API prefixes (/solve, /compare, /batches, ...) are also
// SPA page paths (SolvePage at /solve, ComparePage at /compare, ...). A plain
// prefix-based proxy would swallow full-page GET requests for those paths too
// (e.g. hitting F5 on /solve), forwarding them to the backend and getting a
// JSON 404/405 back instead of index.html. Browser navigations send
// `Accept: text/html...` first; fetch/XHR calls from our own api/client.ts do
// not — so bypass the proxy (let Vite serve the SPA) for html-accepting
// requests and only proxy actual API calls.
function apiProxy(): ProxyOptions {
  return {
    target: backendTarget,
    bypass(req) {
      const accept = req.headers.accept ?? ''
      if (accept.includes('text/html')) return req.url
      return undefined
    },
  }
}

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/auth': apiProxy(),
      '/solve': apiProxy(),
      '/jobs': apiProxy(),
      '/batches': apiProxy(),
      '/solvers': apiProxy(),
      '/tokens': apiProxy(),
      '/compare': apiProxy(),
      '/system': apiProxy(),
      '/users': apiProxy(),
      '/qore-versions': apiProxy(),
    },
  },
})
