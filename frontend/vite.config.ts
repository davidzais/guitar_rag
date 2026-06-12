import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'
import { TanStackRouterVite } from '@tanstack/router-plugin/vite'
import path from 'path'

export default defineConfig({
  plugins: [
    TanStackRouterVite({ routesDirectory: './src/routes' }),
    react(),
    tailwindcss(),
  ],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
    // Force a single React instance. With pnpm's symlinked node_modules, Vite can
    // otherwise resolve react/react-dom as two separate instances (app vs. a dep
    // like Clerk), which breaks hooks ("Cannot read properties of null (useEffect)").
    dedupe: ['react', 'react-dom'],
  },
})