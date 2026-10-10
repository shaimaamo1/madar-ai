import { defineConfig } from '@playwright/test';
export default defineConfig({ testDir: './e2e', workers: 1, use: { baseURL: process.env.MADAR_E2E_BASE_URL || 'http://127.0.0.1:8000', headless: true, launchOptions: { executablePath: process.env.MADAR_CHROMIUM_PATH || '/usr/bin/chromium', args: ['--no-sandbox'] } }, reporter: [['list']], timeout: 30000 });
