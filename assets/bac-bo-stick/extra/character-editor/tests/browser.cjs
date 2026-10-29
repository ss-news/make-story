const {chromium}=require('playwright');const assert=require('node:assert/strict');const fs=require('node:fs');const path=require('node:path');
(async()=>{
const out=path.resolve('output/stung_treng/character-editor/qa');fs.mkdirSync(out,{recursive:true});
const browser=await chromium.launch({executablePath:'/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',headless:true});const page=await browser.newPage({viewport:{width:1440,height:1100}});const errors=[];page.on('pageerror',e=>errors.push(e.message));
try{
 await page.goto('http://127.0.0.1:8766');await page.evaluate(()=>localStorage.clear());await page.reload();await page.locator('.layer').first().waitFor();await page.waitForFunction(()=>document.querySelector('#save-state').textContent.includes('trình duyệt'));
 assert.equal(await page.locator('.layer').count(),17);
 await page.getByRole('button',{name:'Đầu / biểu cảm',exact:true}).click();
 const oldX=+(await page.locator('#field-x').inputValue());const oldY=+(await page.locator('#field-y').inputValue());const box=await page.locator('#canvas').boundingBox();
 const at=(x,y)=>({x:box.x+x/1000*box.width,y:box.y+y/800*box.height});let start=at(oldX,oldY);
 const oldWidth=+(await page.locator('#field-width').inputValue()),oldHeight=+(await page.locator('#field-height').inputValue());
 const corner=at(oldX+oldWidth/2,oldY+oldHeight/2);await page.mouse.move(corner.x,corner.y);await page.mouse.down();await page.mouse.move(corner.x+10/1000*box.width,corner.y+10/800*box.height,{steps:4});await page.mouse.up();assert.ok(+(await page.locator('#field-width').inputValue())>oldWidth+19);await page.locator('#undo').click();
 const rot=at(oldX,oldY-oldHeight/2-28),rotEnd=at(oldX+100,oldY-100);await page.mouse.move(rot.x,rot.y);await page.mouse.down();await page.mouse.move(rotEnd.x,rotEnd.y,{steps:5});await page.mouse.up();assert.ok(+(await page.locator('#field-rotation').inputValue())>30);await page.locator('#undo').click();
 await page.mouse.move(start.x,start.y);await page.mouse.down();await page.mouse.move(start.x+30/1000*box.width,start.y+20/800*box.height,{steps:8});await page.mouse.up();
 assert.ok(Math.abs(+(await page.locator('#field-x').inputValue())-oldX-30)<1);await page.locator('#undo').click();assert.equal(+(await page.locator('#field-x').inputValue()),oldX);await page.locator('#redo').click();
 await page.getByRole('button',{name:'Sợ hãi',exact:true}).click();assert.ok((await page.locator('#selected-image').getAttribute('src')).endsWith('head_scared'));
 await page.locator('#field-rotation').fill('25');await page.locator('#field-rotation').press('Tab');
 const before=await page.evaluate(()=>JSON.parse(localStorage.getItem('stung-treng-character-layout-v1')));
 await page.locator('#field-pivotX').fill('30');await page.locator('#field-pivotX').press('Tab');
 const after=await page.evaluate(()=>JSON.parse(localStorage.getItem('stung-treng-character-layout-v1')));assert.equal(after.parts.find(p=>p.id==='head').pivotX,.3);
 await page.locator('#save-name').fill('qa-layout');await page.locator('#save').click();await page.waitForFunction(()=>document.querySelector('#save-state').textContent.includes('Đã lưu file'));
 const disk=JSON.parse(fs.readFileSync('output/stung_treng/character-editor/layouts/qa-layout.json','utf8'));assert.deepEqual(disk,after);
 await page.reload();await page.locator('.layer').first().waitFor();assert.equal(+(await page.locator('#field-pivotX').inputValue()),50);await page.getByRole('button',{name:'Đầu / biểu cảm',exact:true}).click();assert.equal(+(await page.locator('#field-pivotX').inputValue()),30);
 const downloadPromise=page.waitForEvent('download');await page.locator('#export').click();const dl=await downloadPromise;await dl.saveAs(path.join(out,'export.json'));assert.deepEqual(JSON.parse(fs.readFileSync(path.join(out,'export.json'),'utf8')),disk);
 await page.locator('#file').setInputFiles({name:'bad.json',mimeType:'application/json',buffer:Buffer.from('{"format":"wrong"}')});await page.waitForFunction(()=>document.querySelector('#notice').textContent.includes('Không nhập được'));assert.equal(await page.evaluate(()=>JSON.parse(localStorage.getItem('stung-treng-character-layout-v1')).parts.find(p=>p.id==='head').pivotX),.3);
 // Restore from disk after a deliberate edit, then valid import roundtrip.
 await page.locator('#field-x').fill('550');await page.locator('#field-x').press('Tab');page.once('dialog',d=>d.accept());await page.locator('#saved').selectOption('qa-layout');await page.locator('#load').click();await page.waitForFunction(()=>document.querySelector('#save-state').textContent.includes('Đã mở'));
 assert.equal(await page.evaluate(()=>JSON.parse(localStorage.getItem('stung-treng-character-layout-v1')).parts.find(p=>p.id==='head').x),disk.parts.find(p=>p.id==='head').x);
 await page.locator('#file').setInputFiles({name:'good.json',mimeType:'application/json',buffer:Buffer.from(JSON.stringify(disk))});await page.waitForFunction(()=>document.querySelector('#notice').textContent.includes('Đã nhập cấu hình'));
 // Pointer pivot editing must preserve every image corner.
 const cornerBefore=await page.evaluate(async()=>{const {worldPoint}=await import('/model.js');return worldPoint(JSON.parse(localStorage.getItem('stung-treng-character-layout-v1')).parts.find(p=>p.id==='head'),0,0);});
 await page.locator('#pivot').click();const pivotPos=at(disk.parts.find(p=>p.id==='head').x,disk.parts.find(p=>p.id==='head').y);await page.mouse.move(pivotPos.x,pivotPos.y);await page.mouse.down();await page.mouse.move(pivotPos.x+12,pivotPos.y+8,{steps:4});await page.mouse.up();
 const cornerAfter=await page.evaluate(async()=>{const {worldPoint}=await import('/model.js');return worldPoint(JSON.parse(localStorage.getItem('stung-treng-character-layout-v1')).parts.find(p=>p.id==='head'),0,0);});assert.ok(Math.hypot(cornerBefore.x-cornerAfter.x,cornerBefore.y-cornerAfter.y)<1e-6);await page.locator('#undo').click();await page.locator('#move').click();
 await page.locator('#front').click();assert.equal(+(await page.locator('#field-z').inputValue()),13);await page.locator('#undo').click();await page.locator('#visible').uncheck();assert.ok(await page.locator('.layer.active').evaluate(e=>e.classList.contains('hidden')));await page.locator('#undo').click();
 await page.locator('#pose').selectOption('aim');await page.locator('#play').click();await page.waitForTimeout(250);await page.locator('#play').click();assert.equal(await page.evaluate(()=>JSON.parse(localStorage.getItem('stung-treng-character-layout-v1')).parts.find(p=>p.id==='head').asset),'head_scared');
 await page.locator('#pose').selectOption('edit');await page.locator('#background').selectOption('scene');await page.screenshot({path:path.join(out,'desktop.png'),fullPage:true});
 const pngPromise=page.waitForEvent('download');await page.locator('#png').click();await (await pngPromise).saveAs(path.join(out,'character.png'));
 // Same-origin endpoint and traversal protections.
 const security=await page.evaluate(async()=>{
  const get=async p=>(await fetch(p)).status;
  return {traversal:await get('/api/configs/%2E%2E%2Fbad'),privateFile:await get('/serve.py'),invalid:(await fetch('/api/configs/invalid',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({format:'wrong'})})).status};
 });assert.deepEqual(security,{traversal:400,privateFile:404,invalid:400});
 await page.setViewportSize({width:390,height:844});await page.screenshot({path:path.join(out,'mobile.png'),fullPage:true});assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));
 assert.deepEqual(errors,[]);console.log('Browser: drag, undo/redo, expression, pivot, autosave/reload, disk save, export, invalid import, poses, PNG, responsive layout and API rejection passed.');
}finally{await browser.close();}
})().catch(e=>{console.error(e);process.exit(1);});
