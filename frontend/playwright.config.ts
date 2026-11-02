import { defineConfig } from '@playwright/test';
import { existsSync } from 'node:fs';
export default defineConfig({
  testDir:'./e2e', timeout:45000, workers:1, fullyParallel:false,
  use:{baseURL:'http://127.0.0.1:8000',headless:true,viewport:{width:1440,height:1020},
    launchOptions:{executablePath:process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH||(existsSync('/usr/bin/chromium')?'/usr/bin/chromium':undefined),args:['--no-sandbox','--enable-unsafe-swiftshader']},
    screenshot:'only-on-failure'},
  reporter:'list'
});
