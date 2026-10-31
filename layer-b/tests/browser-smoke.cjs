// Optional browser integration check; uses an isolated synthetic workspace.
const { chromium } = require('playwright');
const { spawn } = require('node:child_process');
const { mkdtemp, rm, mkdir } = require('node:fs/promises');
const { tmpdir } = require('node:os');
const path = require('node:path');

(async () => {
  const directory = await mkdtemp(path.join(tmpdir(), 'civic-portfolio-'));
  const child = spawn(process.env.PYTHON || 'python', ['-m','civic_portfolio','--db',path.join(directory,'test.sqlite3'),'serve','--port','0']);
  let browser;
  try {
    const url = await new Promise((resolve,reject) => {
      const timer=setTimeout(()=>reject(new Error('Application startup timeout')),10000);
      child.stdout.on('data',chunk=>{const match=chunk.toString().match(/http:\/\/127\.0\.0\.1:\d+/);if(match){clearTimeout(timer);resolve(match[0]);}});
      child.on('error',reject);child.on('exit',code=>{clearTimeout(timer);reject(new Error(`Application exited: ${code}`));});
      child.stderr.on('data',chunk=>process.stderr.write(chunk));
    });
    browser=await chromium.launch({headless:true});
    const page=await browser.newPage({viewport:{width:1440,height:1000}}), errors=[];
    page.on('pageerror',error=>errors.push(error.message));
    await page.goto(url);
    await page.getByRole('heading',{name:'Permits, Licenses, and Inspections.'}).waitFor();
    if(await page.locator('#projects button').count()!==50)throw Error('Expected all 50 projects');
    await page.locator('#actor').fill('SYNTHETIC UI TEST');
    await page.getByLabel('Accountable owner',{exact:true}).fill('SYNTHETIC OWNER');
    await page.getByLabel('Scope and requirements',{exact:true}).fill('Synthetic test workflow');
    await page.getByRole('button',{name:'Save definition',exact:true}).click();
    await page.getByText('Definition saved. Changed requirements reset work evidence; review and confirm the new scope in a separate save.',{exact:true}).waitFor();
    await page.reload();
    await page.getByLabel('Accountable owner',{exact:true}).waitFor();
    if(await page.getByLabel('Accountable owner',{exact:true}).inputValue()!=='SYNTHETIC OWNER')throw Error('Edit did not persist');
    await page.locator('#actor').fill('SYNTHETIC UI TEST');
    const panel=page.locator('#detail details');
    await panel.locator('summary').click();
    await panel.getByLabel('Full source text',{exact:true}).fill('SYNTHETIC SOURCE ONLY. <script>window.bad=true</script>');
    await panel.getByRole('button',{name:'Import source version',exact:true}).click();
    await page.getByText('Source imported. Review the new version before reconfirming scope and work.',{exact:true}).waitFor();
    await panel.locator('summary').click();
    await panel.getByRole('button',{name:'Read current source',exact:true}).click();
    await panel.locator('pre').filter({hasText:'SYNTHETIC SOURCE ONLY'}).waitFor();
    if(await page.evaluate(()=>window.bad))throw Error('Source content executed');
    await panel.getByRole('button',{name:'Record current source review',exact:true}).click();
    await page.locator('#detail summary').filter({hasText:'review recorded'}).waitFor();
    await page.locator('#search').fill('009');
    if(await page.locator('#projects button').count()!==1)throw Error('Search failed');
    await page.locator('#search').fill('');
    await mkdir('.local',{recursive:true});
    await page.screenshot({path:'.local/portfolio-desktop.png'});
    await page.setViewportSize({width:390,height:844});
    await page.screenshot({path:'.local/portfolio-mobile.png'});
    if(await page.evaluate(()=>document.documentElement.scrollWidth>window.innerWidth))throw Error('Mobile horizontal overflow');
    if(errors.length)throw Error(errors.join('; '));
    console.log('PASS: 50 projects, persisted edits, source import/read/review, script escaping, search and desktop/mobile layout');
  } finally {
    if(browser)await browser.close();
    child.kill();
    await new Promise(resolve=>child.exitCode!==null?resolve():child.once('exit',resolve));
    await rm(directory,{recursive:true,force:true});
  }
})().catch(error=>{console.error(error);process.exitCode=1;});
