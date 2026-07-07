import { chromium } from 'playwright';

(async () => {
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext(); // clean — no cookies
  const page = await context.newPage();

  // Capture console logs
  page.on('console', msg => console.log(`[CONSOLE ${msg.type()}]`, msg.text()));
  page.on('pageerror', err => console.log(`[PAGE ERROR]`, err.message));

  console.log('1. Navigating to /auth/login (clean context, no cookies)...');
  await page.goto('http://localhost:3333/auth/login', { waitUntil: 'domcontentloaded', timeout: 30000 });

  // Wait a bit for auto-login to attempt
  await page.waitForTimeout(5000);

  // Wait for auto-login redirect
  console.log('2. Waiting for auto-login redirect...');
  try {
    await page.waitForURL('**/dashboard**', { timeout: 15000 });
    console.log(`3. SUCCESS: Redirected to: ${page.url()}`);
  } catch {
    console.log(`3. TIMEOUT: Stayed on: ${page.url()}`);
  }

  const finalUrl = page.url();
  console.log(`4. Final URL: ${finalUrl}`);

  // Wait for dashboard to render
  await page.waitForTimeout(3000);

  // Check for dashboard content
  const title = await page.title();
  console.log(`5. Page title: ${title}`);

  // Check for dashboard elements
  const hasSidebar = await page.locator('aside, [role="navigation"], nav').count() > 0;
  const hasCharts = await page.locator('canvas, svg, [class*="chart"]').count() > 0;
  const hasKPI = await page.locator('[class*="kpi"], [class*="card"], [class*="metric"]').count() > 0;
  console.log(`6. Sidebar: ${hasSidebar}, Charts: ${hasCharts}, KPI cards: ${hasKPI}`);

  // Get body text (first 500 chars)
  const bodyText = await page.locator('body').textContent();
  console.log(`7. Body preview: ${bodyText?.slice(0, 500)}`);

  // Screenshot
  await page.screenshot({ path: '/tmp/auto-login-dashboard.png', fullPage: true });
  console.log('8. Screenshot saved: /tmp/auto-login-dashboard.png');

  await browser.close();
})();