import { defineConfig, devices } from '@playwright/test'

export default defineConfig({
  testDir: './tests/e2e',
  fullyParallel: false,
  workers: 1,
  timeout: 60000,
  expect: { timeout: 15000 },
  reporter: [['list'], ['html', { open: 'never' }]],
  use: {
    baseURL: 'http://127.0.0.1:5173',
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
  },
  projects: [
    { name: 'desktop-chromium', use: { ...devices['Desktop Chrome'] } },
    { name: 'mobile-chromium', use: { ...devices['Pixel 5'] } },
  ],
  webServer: [
    {
      command: 'backend/.venv/bin/python -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8390',
      url: 'http://127.0.0.1:8390/api/health',
      env: {
        APP_ENV: 'test',
        GLM_API_KEY: '',
        DEEPSEEK_API_KEY: '',
        MODEL_PROVIDER: '',
        MONITORING_ENABLED: 'false',
        IFLYTEK_API_PASSWORD: '',
        LLM_API_KEY: '',
        GEMINI_API_KEY: '',
        SUPERADMIN_PASSWORD: 'e2e-only-not-for-production',
        SUPERADMIN_USERNAME: 'e2e_admin',
        DATABASE_PATH: 'backend/tests/.runtime/e2e.sqlite3',
        UPLOAD_DIR: 'backend/tests/.runtime/uploads',
        REPORT_DIR: 'backend/tests/.runtime/reports',
        ASSISTANT_KNOWLEDGE_DIR: 'backend/tests/.runtime/knowledge',
        DATA_DIR: 'backend/data',
        RULES_DIR: 'backend/rules',
      },
      reuseExistingServer: false,
      timeout: 120000,
    },
    {
      command: 'npm run dev -- --host 127.0.0.1 --port 5173',
      env: { VITE_API_PROXY_TARGET: 'http://127.0.0.1:8390' },
      url: 'http://127.0.0.1:5173',
      reuseExistingServer: true,
      timeout: 120000,
    },
  ],
})
