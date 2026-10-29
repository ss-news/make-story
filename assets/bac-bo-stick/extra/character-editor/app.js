import {labels,assets,clone,defaults,validate,localPoint,worldPoint,movePivot,posed,reorderLayers} from './model.js';
const $=id=>document.getElementById(id),canvas=$('canvas'),ctx=canvas.getContext('2d'),storageKey='stung-treng-character-layout-v1';
let doc=defaults(),selected='torso',mode='move',zoom=1,drag=null,undo=[],redo=[],preview='edit',playing=false,phase=0,lastTime=0,dirty=false;
const images={};let draggedLayer=null;
const assetLabels={...labels,head_front:'Đầu — bình thường',head_turn:'Đầu — nhìn nghiêng',head_scared:'Đầu — sợ hãi',head_blink:'Đầu — nhắm mắt'};
function replaceAsset(asset){if(!assets.includes(asset))return;const p=selectedPart();if(p.asset===asset)return;change(()=>p.asset=asset);notice(`Đã thay ảnh cho ${labels[p.id]} bằng ${assetLabels[asset]}. Các thông số bố cục được giữ nguyên.`);}
function placeLayer(source,target,before){change(()=>{doc=reorderLayers(doc,source,target,before);selected=source;});notice('Đã cập nhật z-index. Lớp ở trên danh sách nằm phía trước.');}
function stepLayer(direction){const order=sorted(doc.parts).reverse(),index=order.findIndex(p=>p.id===selected),target=order[index+direction];if(target)placeLayer(selected,target.id,direction<0);}
function notice(text,error=false){$('notice').textContent=text;$('notice').classList.toggle('error',error);}
function status(text){$('save-state').textContent=text;}
try{const saved=localStorage.getItem(storageKey);if(saved)doc=validate(JSON.parse(saved));}catch{notice('Không đọc được bản tự lưu. Đã mở mẫu gốc; bạn có thể nhập lại JSON.',true);}
async function image(key,url){const img=new Image();img.src=url;await img.decode();images[key]=img;}
function persist(){dirty=true;try{localStorage.setItem(storageKey,JSON.stringify(doc));status('Đã tự lưu trong trình duyệt · chưa lưu file');}catch{status('Chưa tự lưu được');notice('Trình duyệt không cho lưu. Hãy xuất JSON để giữ thay đổi.',true);}}
function checkpoint(){undo.push(clone(doc));if(undo.length>80)undo.shift();redo=[];}
function edit(){playing=false;preview='edit';$('pose').value='edit';$('play').textContent='▶ Chạy thử';$('keep-pose').style.display='none';}
function change(fn){edit();checkpoint();fn();persist();refresh();}
function selectedPart(){return doc.parts.find(p=>p.id===selected)||doc.parts[0];}
function view(){return posed(doc,preview,phase);}
function sorted(parts){return [...parts].sort((a,b)=>a.z-b.z);}
function uiScale(){return canvas.width/canvas.getBoundingClientRect().width/zoom;}
function choose(id){edit();selected=id;$('lock-selection').checked=true;refresh();const list=$('layers'),row=list.querySelector('.active');if(row){const a=row.getBoundingClientRect(),b=list.getBoundingClientRect();if(a.top<b.top)list.scrollTop+=a.top-b.top;else if(a.bottom>b.bottom)list.scrollTop+=a.bottom-b.bottom;}}
function applyTransform(p){ctx.translate(p.x,p.y);ctx.rotate(p.rotation*Math.PI/180);}
function paintPart(p,c=ctx){const img=images[p.asset];if(!p.visible||!img)return;c.save();c.translate(p.x,p.y);c.rotate(p.rotation*Math.PI/180);c.drawImage(img,-p.pivotX*p.width,-p.pivotY*p.height,p.width,p.height);c.restore();}
function draw(){
 const w=doc.canvas.width,h=doc.canvas.height;if(canvas.width!==w||canvas.height!==h){canvas.width=w;canvas.height=h;canvas.style.aspectRatio=`${w}/${h}`;}
 ctx.clearRect(0,0,w,h);const bg=$('background').value;
 if(bg==='scene'&&images.background){const img=images.background,scale=Math.max(w/img.width,h/img.height),dw=img.width*scale,dh=img.height*scale;ctx.drawImage(img,(w-dw)/2,(h-dh)/2,dw,dh);}
 else if(bg==='dark'){ctx.fillStyle='#26322e';ctx.fillRect(0,0,w,h);}
 else{ctx.fillStyle='#fcfcf9';ctx.fillRect(0,0,w,h);ctx.fillStyle='#edf0e8';for(let y=0;y<h;y+=24)for(let x=0;x<w;x+=24)if((x/24+y/24)%2===0)ctx.fillRect(x,y,24,24);}
 ctx.save();ctx.translate(w/2,h/2);ctx.scale(zoom,zoom);ctx.translate(-w/2,-h/2);
 const d=view();for(const p of sorted(d.parts))paintPart(p);
 if($('guides').checked){
  for(const p of d.parts.filter(p=>p.visible)){ctx.beginPath();ctx.arc(p.x,p.y,p.id===selected?6:3.5,0,Math.PI*2);ctx.fillStyle=p.id===selected?'#d97a39':'#ffffffdd';ctx.fill();ctx.strokeStyle=p.id===selected?'#fff':'#527864';ctx.lineWidth=1.5;ctx.stroke();}
 }
 const p=d.parts.find(p=>p.id===selected);if(p&&p.visible){const unit=uiScale();
  ctx.save();applyTransform(p);const x=-p.pivotX*p.width,y=-p.pivotY*p.height;ctx.fillStyle='#db923412';ctx.fillRect(x,y,p.width,p.height);ctx.strokeStyle='#bd6b32';ctx.lineWidth=1.5*unit;ctx.setLineDash([6*unit,4*unit]);ctx.strokeRect(x,y,p.width,p.height);ctx.setLineDash([]);
  for(const [a,b] of [[x,y],[x+p.width,y],[x,y+p.height],[x+p.width,y+p.height]]){ctx.fillStyle='#fff';ctx.fillRect(a-5*unit,b-5*unit,10*unit,10*unit);ctx.strokeRect(a-5*unit,b-5*unit,10*unit,10*unit);}
  const handle=worldPoint(p,p.width/2,-32*unit),top=worldPoint(p,p.width/2,0);
  ctx.restore();ctx.beginPath();ctx.moveTo(top.x,top.y);ctx.lineTo(handle.x,handle.y);ctx.strokeStyle='#bd6b32';ctx.stroke();ctx.beginPath();ctx.arc(handle.x,handle.y,7*unit,0,Math.PI*2);ctx.fillStyle='#fff';ctx.fill();ctx.stroke();
  ctx.beginPath();ctx.arc(p.x,p.y,8*unit,0,Math.PI*2);ctx.fillStyle='#d8773b';ctx.fill();ctx.strokeStyle='white';ctx.lineWidth=2*unit;ctx.stroke();ctx.beginPath();ctx.moveTo(p.x-4*unit,p.y);ctx.lineTo(p.x+4*unit,p.y);ctx.moveTo(p.x,p.y-4*unit);ctx.lineTo(p.x,p.y+4*unit);ctx.stroke();
 }
 ctx.restore();
}
const fieldSpecs=[['x','Vị trí X','px'],['y','Vị trí Y','px'],['width','Chiều rộng','px'],['height','Chiều cao','px'],['rotation','Góc xoay','°'],['z','Z-index',''],['pivotX','Điểm xoay X','%'],['pivotY','Điểm xoay Y','%']];
for(const [key,label,unit] of fieldSpecs){const l=document.createElement('label');l.textContent=`${label} ${unit}`;const input=document.createElement('input');input.type='number';input.id='field-'+key;input.step=key.startsWith('pivot')?'1':'.5';input.setAttribute('aria-label',label);l.append(input);$('fields').append(l);
 input.addEventListener('change',()=>{const value=Number(input.value),p=selectedPart();if(input.value.trim()===''||!Number.isFinite(value)){refresh();return;}
  const candidate=clone(doc),target=candidate.parts.find(t=>t.id===p.id);
  if(key.startsWith('pivot'))movePivot(target,key==='pivotX'?value/100:p.pivotX,key==='pivotY'?value/100:p.pivotY);else target[key]=value;
  try{validate(candidate);change(()=>doc=candidate);}catch(e){notice(e.message,true);refresh();}
 });
}
function refresh(){
 const p=selectedPart();selected=p.id;$('selected-label').textContent=labels[p.id];$('selected-image').src='/source/'+p.asset;$('asset-select').value=p.asset;$('restore-asset').disabled=p.asset===(p.id==='head'?'head_front':p.id);for(const tile of $('asset-grid').children){const active=tile.dataset.asset===p.asset;tile.classList.toggle('active',active);tile.setAttribute('aria-pressed',String(active));}$('visible').checked=p.visible;$('doc-title').textContent=doc.title||'Nhân vật áo kem';$('count').textContent=doc.parts.length;
 for(const [key] of fieldSpecs)$('field-'+key).value=+(p[key]*(key.startsWith('pivot')?100:1)).toFixed(2);
 $('undo').disabled=!undo.length;$('redo').disabled=!redo.length;const listScroll=$('layers').scrollTop;$('layers').replaceChildren();
 const quick=$('part-select');quick.replaceChildren();for(const part of doc.parts){const o=new Option(labels[part.id]+(part.visible?'':' · đang ẩn'),part.id);quick.append(o);}quick.value=selected;
 $('selection-help').textContent=$('lock-selection').checked?`Đang giữ: ${labels[p.id]}. Kéo trên khung để di chuyển; các mảnh khác không bị chọn nhầm.`:'Bấm trên hình để chọn, hoặc chọn chính xác từ danh sách.';
 const fold=value=>value.toLocaleLowerCase('vi').normalize('NFD').replace(/[\u0300-\u036f]/g,'').replace(/đ/g,'d');const query=fold($('part-search').value.trim());let matches=0;
 for(const part of sorted(doc.parts).reverse()){
  if(query&&!fold(labels[part.id]).includes(query))continue;matches++;
  const b=document.createElement('button');b.className='layer'+(part.id===selected?' active':'')+(part.visible?'':' hidden');b.dataset.id=part.id;b.setAttribute('aria-label',labels[part.id]);b.setAttribute('aria-pressed',String(part.id===selected));
  const img=document.createElement('img');img.src='/source/'+part.asset;img.alt='';const name=document.createElement('span');name.className='name';name.textContent=labels[part.id];
  const grip=document.createElement('span');grip.className='layer-grip';grip.textContent='⠿';grip.title='Kéo để xếp lớp';const badge=document.createElement('span');badge.className='z-badge';badge.textContent='z '+part.z;badge.title='Z-index: số lớn nằm trước';
  b.draggable=true;b.ondragstart=e=>{draggedLayer=part.id;e.dataTransfer.setData('text/plain',part.id);e.dataTransfer.effectAllowed='move';b.classList.add('dragging');};
  b.ondragover=e=>{if(!draggedLayer||draggedLayer===part.id)return;e.preventDefault();e.dataTransfer.dropEffect='move';const before=e.clientY<b.getBoundingClientRect().top+b.offsetHeight/2;b.classList.toggle('drop-before',before);b.classList.toggle('drop-after',!before);};
  b.ondragleave=()=>b.classList.remove('drop-before','drop-after');b.ondragend=()=>{draggedLayer=null;for(const row of $('layers').children)row.classList.remove('dragging','drop-before','drop-after');};
  b.ondrop=e=>{e.preventDefault();const source=draggedLayer;draggedLayer=null;b.classList.remove('drop-before','drop-after');if(source&&source!==part.id)placeLayer(source,part.id,e.clientY<b.getBoundingClientRect().top+b.offsetHeight/2);};
  b.onkeydown=e=>{if(e.altKey&&['ArrowUp','ArrowDown'].includes(e.key)){e.preventDefault();e.stopPropagation();selected=part.id;stepLayer(e.key==='ArrowUp'?-1:1);}};
  const eye=document.createElement('span');eye.className='eye';eye.textContent=part.visible?'◉':'○';eye.title=part.visible?'Đang hiện':'Đang ẩn';img.draggable=false;b.append(grip,img,name,badge,eye);b.onclick=e=>{if(e.target===eye)change(()=>part.visible=!part.visible);else choose(part.id);};$('layers').append(b);
 }
 $('list-empty').hidden=matches!==0;$('layers').scrollTop=listScroll;
 for(const b of $('faces').children)b.classList.toggle('active',doc.parts.find(p=>p.id==='head')?.asset===b.dataset.asset);
 draw();
}
for(const [asset,label] of [['head_front','Bình thường'],['head_turn','Nhìn nghiêng'],['head_scared','Sợ hãi'],['head_blink','Nhắm mắt']]){
 const b=document.createElement('button');b.dataset.asset=asset;b.innerHTML=`<img src="/source/${asset}" alt="">${label}`;b.onclick=()=>{const head=doc.parts.find(p=>p.id==='head');if(!head)return notice('Bản nhập không có đầu để đổi biểu cảm.',true);change(()=>{head.asset=asset;selected='head';});};$('faces').append(b);
}
for(const asset of assets){
 $('asset-select').append(new Option(assetLabels[asset],asset));
 const tile=document.createElement('button');tile.className='asset-tile';tile.dataset.asset=asset;tile.title=assetLabels[asset];tile.setAttribute('aria-label','Dùng ảnh '+assetLabels[asset]);
 const img=document.createElement('img');img.src='/source/'+asset;img.alt='';const label=document.createElement('span');label.textContent=assetLabels[asset];tile.append(img,label);tile.onclick=()=>replaceAsset(asset);$('asset-grid').append(tile);
}
$('asset-select').onchange=()=>replaceAsset($('asset-select').value);
$('restore-asset').onclick=()=>replaceAsset(selected==='head'?'head_front':selected);
$('asset-library').onclick=()=>{const grid=$('asset-grid');grid.hidden=!grid.hidden;$('asset-library').setAttribute('aria-expanded',String(!grid.hidden));$('asset-library').textContent=grid.hidden?'Chọn bằng hình':'Ẩn bộ ảnh';};
$('part-select').onchange=()=>choose($('part-select').value);
$('part-search').oninput=()=>{$('layers').scrollTop=0;refresh();};
$('lock-selection').onchange=refresh;
function pointer(e){const r=canvas.getBoundingClientRect(),x=(e.clientX-r.left)/r.width*canvas.width,y=(e.clientY-r.top)/r.height*canvas.height;return {x:(x-canvas.width/2)/zoom+canvas.width/2,y:(y-canvas.height/2)/zoom+canvas.height/2};}
canvas.addEventListener('pointerdown',e=>{
 if(e.button!==0)return;if(preview!=='edit'){edit();draw();}canvas.focus();const pos=pointer(e),current=selectedPart(),unit=uiScale();
 const startMove=part=>{selected=part.id;checkpoint();drag={kind:'move',x:pos.x,y:pos.y,before:clone(part)};canvas.setPointerCapture(e.pointerId);refresh();};
 if(mode==='move'&&current.visible){
  if(Math.hypot(pos.x-current.x,pos.y-current.y)<15*unit){startMove(current);return;}
  const rot=worldPoint(current,current.width/2,-32*unit);
  if(Math.hypot(pos.x-rot.x,pos.y-rot.y)<16*unit){checkpoint();drag={kind:'rotate',angle:Math.atan2(pos.y-current.y,pos.x-current.x),before:clone(current)};canvas.setPointerCapture(e.pointerId);return;}
  for(const [u,v] of [[0,0],[1,0],[0,1],[1,1]]){const c=worldPoint(current,u*current.width,v*current.height);
   if(Math.hypot(pos.x-c.x,pos.y-c.y)<14*unit){checkpoint();drag={kind:'resize',u,v,before:clone(current)};canvas.setPointerCapture(e.pointerId);return;}}
 }
 if(mode==='pivot'&&current.visible){const lp=localPoint(current,pos.x,pos.y);if(lp.x>=0&&lp.x<=current.width&&lp.y>=0&&lp.y<=current.height){checkpoint();drag={kind:'pivot',before:clone(current)};canvas.setPointerCapture(e.pointerId);return;}}
 if($('lock-selection').checked){if(current.visible&&mode==='move')startMove(current);else notice(current.visible?'Kéo bên trong mảnh để đặt điểm xoay.':'Bộ phận đang ẩn. Bật “Hiển thị bộ phận” trước khi kéo.',true);return;}
 if(current.visible&&mode==='move'){const lp=localPoint(current,pos.x,pos.y),pad=10*unit;if(lp.x>=-pad&&lp.y>=-pad&&lp.x<=current.width+pad&&lp.y<=current.height+pad){startMove(current);return;}}
 const hit=sorted(doc.parts).reverse().find(p=>{if(!p.visible)return false;const t=localPoint(p,pos.x,pos.y);if(t.x<0||t.y<0||t.x>p.width||t.y>p.height)return false;
  const img=images[p.asset];if(!img)return false;const sample=document.createElement('canvas');sample.width=1;sample.height=1;const sc=sample.getContext('2d');sc.drawImage(img,t.x/p.width*img.width,t.y/p.height*img.height,1,1,0,0,1,1);return sc.getImageData(0,0,1,1).data[3]>20;});
 if(hit)startMove(hit);
});
canvas.addEventListener('pointermove',e=>{if(!drag){canvas.style.cursor=mode==='pivot'?'crosshair':'grab';return;}const p=selectedPart(),pos=pointer(e);
 if(drag.kind==='move'){p.x=Math.max(-8192,Math.min(8192,drag.before.x+pos.x-drag.x));p.y=Math.max(-8192,Math.min(8192,drag.before.y+pos.y-drag.y));}
 else if(drag.kind==='rotate'){const angle=Math.atan2(pos.y-p.y,pos.x-p.x)-drag.angle;p.rotation=((drag.before.rotation+angle*180/Math.PI+540)%360)-180;}
 else if(drag.kind==='resize'){const lp=localPoint(drag.before,pos.x,pos.y),dx=drag.u-p.pivotX,dy=drag.v-p.pivotY;
  if(Math.abs(dx)>.01)p.width=Math.max(1,Math.min(4096,(lp.x-drag.before.pivotX*drag.before.width)/dx));
  if(Math.abs(dy)>.01)p.height=Math.max(1,Math.min(4096,(lp.y-drag.before.pivotY*drag.before.height)/dy));
 }
 else{const lp=localPoint(drag.before,pos.x,pos.y);Object.assign(p,clone(drag.before));movePivot(p,Math.max(0,Math.min(1,lp.x/p.width)),Math.max(0,Math.min(1,lp.y/p.height)));}
 for(const [key] of fieldSpecs)$('field-'+key).value=+(p[key]*(key.startsWith('pivot')?100:1)).toFixed(2);draw();
});
function endDrag(){if(drag){drag=null;persist();refresh();}}
canvas.addEventListener('pointerup',endDrag);canvas.addEventListener('pointercancel',endDrag);
$('visible').onchange=()=>change(()=>selectedPart().visible=$('visible').checked);
$('move').onclick=()=>{mode='move';$('move').classList.add('active');$('pivot').classList.remove('active');$('mode-note').textContent='Kéo chấm cam hoặc kéo trong vùng đang chọn';};
$('pivot').onclick=()=>{mode='pivot';$('pivot').classList.add('active');$('move').classList.remove('active');$('mode-note').textContent='Chọn mảnh bên trái, kéo trên ảnh để đặt điểm xoay';};
$('undo').onclick=()=>{if(!undo.length)return;edit();redo.push(clone(doc));doc=undo.pop();persist();refresh();};
$('redo').onclick=()=>{if(!redo.length)return;edit();undo.push(clone(doc));doc=redo.pop();persist();refresh();};
$('layer-up').onclick=()=>stepLayer(-1);$('layer-down').onclick=()=>stepLayer(1);
$('front').onclick=()=>change(()=>selectedPart().z=Math.min(100,Math.max(...doc.parts.map(p=>p.z))+1));
$('back').onclick=()=>change(()=>selectedPart().z=Math.max(-100,Math.min(...doc.parts.map(p=>p.z))-1));
$('reset').onclick=()=>{if(confirm('Khôi phục toàn bộ nhân vật về mẫu ban đầu? Bạn vẫn có thể hoàn tác.'))change(()=>doc=defaults());};
$('zoom').oninput=()=>{zoom=+$('zoom').value/100;$('zoom-value').textContent=$('zoom').value+'%';draw();};
$('background').onchange=draw;$('guides').onchange=draw;
$('pose').onchange=()=>{preview=$('pose').value;phase=0;$('keep-pose').style.display=preview==='edit'?'none':'inline-block';notice(preview==='edit'?'Đang chỉnh bản gốc.':'Đang xem thử. Chọn “Giữ tư thế” nếu muốn lưu tư thế này vào bản chỉnh.');draw();};
$('keep-pose').onclick=()=>{const candidate=view();try{validate(candidate);change(()=>doc=candidate);}catch(e){notice(e.message,true);}};
$('play').onclick=()=>{if(playing){playing=false;$('play').textContent='▶ Chạy thử';return;}if(preview==='edit'){preview='walk';$('pose').value='walk';$('keep-pose').style.display='inline-block';}playing=true;lastTime=performance.now();$('play').textContent='Ⅱ Tạm dừng';};
function loop(t){if(playing){phase+=Math.min(.1,(t-lastTime)/1000)*5;draw();}lastTime=t;requestAnimationFrame(loop);}requestAnimationFrame(loop);
function download(blob,name){const a=document.createElement('a'),url=URL.createObjectURL(blob);a.href=url;a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);}
$('export').onclick=()=>{download(new Blob([JSON.stringify(doc,null,2)],{type:'application/json'}),($('save-name').value||'nhan-vat')+'.json');notice('Đã xuất bản chỉnh gốc ra JSON. Tư thế xem thử chỉ được lưu khi bạn chọn “Giữ tư thế”.');};
$('png').onclick=()=>{const c=document.createElement('canvas');c.width=doc.canvas.width;c.height=doc.canvas.height;const cc=c.getContext('2d');for(const p of sorted(view().parts))paintPart(p,cc);c.toBlob(blob=>{if(blob)download(blob,'nhan-vat-preview.png');else notice('Không xuất được PNG.',true);});};
$('import').onclick=()=>$('file').click();$('file').onchange=async()=>{const f=$('file').files[0];if(!f)return;try{if(f.size>100000)throw Error('File quá lớn (tối đa 100 KB).');const imported=validate(JSON.parse(await f.text()));change(()=>doc=imported);notice('Đã nhập cấu hình. Bạn có thể hoàn tác để quay về bản trước.');}catch(e){notice('Không nhập được: '+e.message,true);}$('file').value='';};
async function request(path,options){const r=await fetch(path,options);const body=await r.json();if(!r.ok)throw Error(body.error||'Không kết nối được máy chủ.');return body;}
async function listSaves(chosen){const data=await request('/api/configs');$('saved').replaceChildren();for(const name of data.names){const o=document.createElement('option');o.value=name;o.textContent=name;$('saved').append(o);}if(!data.names.length){const o=new Option('Chưa có bản lưu','');$('saved').append(o);}if(chosen)$('saved').value=chosen;}
async function save(){try{validate(doc);const name=$('save-name').value;if(!/^[a-zA-Z0-9_-]{1,80}$/.test(name))throw Error('Tên file chỉ gồm chữ không dấu, số, dấu - hoặc _.');
 const response=await request('/api/configs/'+encodeURIComponent(name),{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(doc)});dirty=false;status('Đã lưu file · '+name);notice('Đã lưu: '+response.path);await listSaves(name);
 }catch(e){notice('Chưa lưu file: '+e.message+' Bạn có thể dùng Xuất JSON.',true);}}
$('save').onclick=save;$('save-copy').onclick=save;
$('load').onclick=async()=>{const name=$('saved').value;if(!name)return;try{if(dirty&&!confirm('Mở bản đã lưu? Bản đang chỉnh có thể khôi phục bằng Hoàn tác.'))return;const imported=validate(await request('/api/configs/'+encodeURIComponent(name)));change(()=>doc=imported);$('save-name').value=name;dirty=false;status('Đã mở · '+name);notice('Đã mở bản '+name+'.');}catch(e){notice(e.message,true);}};
window.addEventListener('keydown',e=>{if(['INPUT','SELECT','TEXTAREA'].includes(document.activeElement.tagName))return;
 if((e.metaKey||e.ctrlKey)&&e.key.toLowerCase()==='z'){e.preventDefault();$(e.shiftKey?'redo':'undo').click();return;}
 const dir={ArrowLeft:[-1,0],ArrowRight:[1,0],ArrowUp:[0,-1],ArrowDown:[0,1]}[e.key];if(dir){e.preventDefault();change(()=>{const p=selectedPart(),n=e.shiftKey?10:1;p.x=Math.max(-8192,Math.min(8192,p.x+dir[0]*n));p.y=Math.max(-8192,Math.min(8192,p.y+dir[1]*n));});}
});
new ResizeObserver(()=>draw()).observe(canvas);
try{await Promise.all([...assets.map(key=>image(key,'/source/'+key)),image('background','/source/background')]);refresh();status('Bản nháp tự lưu trên trình duyệt');await listSaves();}catch(e){notice('Không tải được ảnh hoặc danh sách bản lưu. Kiểm tra máy chủ rồi tải lại trang. '+e.message,true);}
