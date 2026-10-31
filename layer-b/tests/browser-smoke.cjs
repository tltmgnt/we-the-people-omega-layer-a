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
    await page.goto(url+'/permits');
    await page.getByRole('heading',{name:'Synthetic permit lab'}).waitFor();
    await page.getByText('No fictional cases yet. No baseline is assumed.',{exact:true}).waitFor();
    await page.locator('#actor').fill('SYNTHETIC UI TEST');
    await page.locator('#asof').fill('2026-01-02T00:00:00Z');
    await page.locator('#case-id').fill('SYN-BROWSER');
    await page.locator('#case-category').fill('Fictional test category');
    await page.locator('#received').fill('2026-01-01T00:00:00Z');
    await page.locator('#case-evidence').fill('SYNTHETIC browser-test intake');
    await page.getByRole('button',{name:'Create synthetic case',exact:true}).click();
    await page.getByRole('heading',{name:'SYN-BROWSER',exact:true}).waitFor();
    for(const [stage,hour] of [['IN_REVIEW','01'],['INSPECTION','02'],['DECIDED','03']]){
      await page.getByLabel('Next synthetic stage',{exact:true}).selectOption(stage);
      await page.getByLabel('Event timestamp',{exact:true}).fill(`2026-01-01T${hour}:00:00Z`);
      await page.getByLabel('Event evidence / scenario',{exact:true}).fill('SYNTHETIC stage result');
      await page.getByRole('button',{name:'Record synthetic stage',exact:true}).click();
      await page.locator('#detail > p').filter({hasText:'Fictional test category · '+stage}).waitFor();
    }
    await page.getByLabel('Quality-review timestamp',{exact:true}).fill('2026-01-01T04:00:00Z');
    await page.getByLabel('Quality criteria and review evidence',{exact:true}).fill('SYNTHETIC checked criteria');
    await page.getByRole('button',{name:'Record quality review',exact:true}).click();
    await page.locator('#detail li').filter({hasText:'SYNTHETIC checked criteria'}).waitFor();
    await page.getByRole('button',{name:'Refresh report',exact:true}).click();
    await page.waitForFunction(()=>JSON.parse(document.getElementById('report-data').textContent).quality_sample_size===1);
    const report=JSON.parse(await page.locator('#report-data').textContent());
    if(report.decided!==1||report.elapsed_calendar_hours.median!==3||report.quality_pass_rate!==1)throw Error('Permit report mismatch');
    await page.screenshot({path:'.local/portfolio-permit-mobile.png'});
    if(await page.evaluate(()=>document.documentElement.scrollWidth>window.innerWidth))throw Error('Permit mobile overflow');
    await page.reload();
    await page.getByRole('heading',{name:'SYN-BROWSER',exact:true}).waitFor();
    await page.getByRole('heading',{name:'Synthetic quality review',exact:true}).waitFor();
    if(errors.length)throw Error(errors.join('; '));
    console.log('PASS: portfolio and synthetic permit lifecycle, reports, persisted records and mobile layout');
  } finally {
    if(browser)await browser.close();
    child.kill();
    await new Promise(resolve=>child.exitCode!==null?resolve():child.once('exit',resolve));
    await rm(directory,{recursive:true,force:true});
  }
})().catch(error=>{console.error(error);process.exitCode=1;});
