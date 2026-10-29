const {chromium}=require('playwright');const assert=require('node:assert/strict');
(async()=>{const browser=await chromium.launch({executablePath:'/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',headless:true});const page=await browser.newPage({viewport:{width:1280,height:950}});const errors=[];page.on('pageerror',e=>errors.push(e.message));
try{await page.goto('http://127.0.0.1:8766');await page.locator('.layer').first().waitFor();
 await page.locator('#part-select').waitFor({state:'visible',timeout:2000});
 await page.locator('#part-select').selectOption('forearm_l');assert.equal(await page.locator('#selected-label').textContent(),'Cẳng tay bên trái');
 await page.locator('#part-search').fill('cang tay');assert.equal(await page.locator('.layer').count(),2);await page.locator('#part-search').fill('');
 // Selected thin/overlapped artwork must be draggable from a visible move handle, without pixel hunting.
 const doc=await page.evaluate(async()=>{const {defaults}=await import('/model.js');return defaults();});const p=doc.parts.find(p=>p.id==='forearm_l');const box=await page.locator('#canvas').boundingBox();const at=(x,y)=>({x:box.x+x/1000*box.width,y:box.y+y/800*box.height});
 const start=at(p.x,p.y),before=+(await page.locator('#field-x').inputValue());
 await page.mouse.move(start.x,start.y);await page.mouse.down();await page.mouse.move(start.x+35,start.y+15,{steps:6});await page.mouse.up();assert.equal(await page.locator('#part-select').inputValue(),'forearm_l');assert.ok(+(await page.locator('#field-x').inputValue())>before+30);await page.locator('#undo').click();
 await page.locator('#part-select').selectOption('shoulder_l');assert.equal(await page.locator('#visible').isChecked(),false);await page.locator('#visible').check();assert.equal(await page.locator('#part-select').inputValue(),'shoulder_l');
 await page.setViewportSize({width:390,height:844});await page.locator('#part-select').selectOption('hand_r');assert.equal(await page.locator('#selected-label').textContent(),'Bàn tay bên phải');assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));
 await page.screenshot({path:'output/stung_treng/character-editor/qa/selection-mobile.png',fullPage:true});assert.deepEqual(errors,[]);console.log('Selection: searchable list, quick select, selected-part drag, hidden pieces and mobile passed.');
}finally{await browser.close();}})().catch(e=>{console.error(e);process.exit(1);});
