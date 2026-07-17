import { defineConfig, loadEnv } from 'vite';
import react from '@vitejs/plugin-react';
import tailwindcss from '@tailwindcss/vite';

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '');

  return {
    plugins: [react(), tailwindcss()],
    server: {
      host: '0.0.0.0',
      port: 4173,
      proxy: {
        '/api': {
          target: 'http://127.0.0.1:8000',
          changeOrigin: true,
          secure: false,
        },
      },
    },
    preview: {
      host: '0.0.0.0',
      port: 4173,
      proxy: {
        '/api': {
          target: 'http://127.0.0.1:8000',
          changeOrigin: true,
          secure: false,
        },
      },
    },
    build: {
      sourcemap: false,
      chunkSizeWarningLimit: 1000,
      rollupOptions: {
        output: {
          manualChunks(id) {
            if (id.includes('node_modules')) {
              if (id.includes('react-router-dom') || id.includes('react-dom') || id.includes('react')) {
                return 'vendor';
              }
              if (id.includes('framer-motion') || id.includes('lucide-react')) {
                return 'ui';
              }
              if (id.includes('react-hook-form') || id.includes('@hookform/resolvers') || id.includes('zod')) {
                return 'form';
              }
              if (id.includes('@tanstack/react-query')) {
                return 'query';
              }
            }
          },
        },
      },
    },
    define: {
      __APP_ENV__: JSON.stringify(env.MODE),
    },
  };
});
