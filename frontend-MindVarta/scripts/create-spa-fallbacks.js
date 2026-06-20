/* global process */
import { copyFileSync, existsSync, mkdirSync } from 'node:fs'
import { join } from 'node:path'

const distDir = join(process.cwd(), 'dist')
const indexFile = join(distDir, 'index.html')

if (!existsSync(indexFile)) {
  throw new Error('dist/index.html was not found. Run this script after vite build.')
}

const clientRoutes = [
  'auth',
  'chat',
  'documentation',
  'forgot-password',
  'reset-password',
]

for (const route of clientRoutes) {
  const routeDir = join(distDir, route)
  mkdirSync(routeDir, { recursive: true })
  copyFileSync(indexFile, join(routeDir, 'index.html'))
}

console.log(`Created SPA fallback pages for ${clientRoutes.length} routes.`)
