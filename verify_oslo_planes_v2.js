const { chromium } = require('playwright');
const path = require('path');

(async () => {
  const browser = await chromium.launch({
    args: ['--disable-web-security']
  });
  const context = await browser.newContext({
    viewport: { width: 1280, height: 720 }
  });
  const page = await context.newPage();

  const filePath = 'file://' + path.resolve('oslo_planes.html');
  console.log('Loading:', filePath);

  await page.goto(filePath);

  // Wait for data to load and render
  console.log('Waiting for aircraft data...');
  await page.waitForFunction(() => {
    const status = document.getElementById('status').textContent;
    return status.includes('aircraft tracked');
  }, { timeout: 30000 });

  const status = await page.textContent('#status');
  console.log('Status:', status);

  // Give it a moment to render icons
  await page.waitForTimeout(2000);

  await page.screenshot({ path: 'oslo_planes_final.png' });
  console.log('Screenshot saved to oslo_planes_final.png');

  await browser.close();
})();
