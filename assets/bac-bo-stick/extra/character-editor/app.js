import {labels,assets,clone,defaults,validate,localPoint,worldPoint,movePivot,posed} from './model.js';
const $=id=>document.getElementById(id),canvas=$('canvas'),ctx=canvas.getContext('2d'),storageKey='stung-treng-character-layout-v1';
let doc=defaults(),selected='torso',mode='move',zoom=1,drag=null,undo=[],redo=[],preview='edit',playing=false,phase=0,lastTime=0,dirty=false;
const images={};
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
 const p=d.parts.find(p=>p.id===selected);if(p&&p.visible){
  ctx.save();applyTransform(p);const x=-p.pivotX*p.width,y=-p.pivotY*p.height;ctx.strokeStyle='#bd6b32';ctx.lineWidth=1.5/zoom;ctx.setLineDash([6/zoom,4/zoom]);ctx.strokeRect(x,y,p.width,p.height);ctx.setLineDash([]);
  for(const [a,b] of [[x,y],[x+p.width,y],[x,y+p.height],[x+p.width,y+p.height]]){ctx.fillStyle='#fff';ctx.fillRect(a-3/zoom,b-3/zoom,6/zoom,6/zoom);ctx.strokeRect(a-3/zoom,b-3/zoom,6/zoom,6/zoom);}
  const handle=worldPoint(p,p.width/2,-28/zoom),top=worldPoint(p,p.width/2,0);
  ctx.restore();ctx.beginPath();ctx.moveTo(top.x,top.y);ctx.lineTo(handle.x,handle.y);ctx.strokeStyle='#bd6b32';ctx.stroke();ctx.beginPath();ctx.arc(handle.x,handle.y,5/zoom,0,Math.PI*2);ctx.fillStyle='#fff';ctx.fill();ctx.stroke();
 }
 ctx.restore();
}
const fieldSpecs=[['x','Vị trí X','px'],['y','Vị trí Y','px'],['width','Chiều rộng','px'],['height','Chiều cao','px'],['rotation','Góc xoay','°'],['z','Thứ tự lớp',''],['pivotX','Điểm xoay X','%'],['pivotY','Điểm xoay Y','%']];
for(const [key,label,unit] of fieldSpecs){const l=document.createElement('label');l.textContent=`${label} ${unit}`;const input=document.createElement('input');input.type='number';input.id='field-'+key;input.step=key.startsWith('pivot')?'1':'.5';input.setAttribute('aria-label',label);l.append(input);$('fields').append(l);
 input.addEventListener('change',()=>{const value=Number(input.value),p=selectedPart();if(input.value.trim()===''||!Number.isFinite(value)){refresh();return;}
  const candidate=clone(doc),target=candidate.parts.find(t=>t.id===p.id);
  if(key.startsWith('pivot'))movePivot(target,key==='pivotX'?value/100:p.pivotX,key==='pivotY'?value/100:p.pivotY);else target[key]=value;
  try{validate(candidate);change(()=>doc=candidate);}catch(e){notice(e.message,true);refresh();}
 });
}
function refresh(){
 const p=selectedPart();selected=p.id;$('selected-label').textContent=labels[p.id];$('selected-image').src='/source/'+p.asset;$('visible').checked=p.visible;$('doc-title').textContent=doc.title||'Nhân vật áo kem';$('count').textContent=doc.parts.length;
 for(const [key] of fieldSpecs)$('field-'+key).value=+(p[key]*(key.startsWith('pivot')?100:1)).toFixed(2);
 $('undo').disabled=!undo.length;$('redo').disabled=!redo.length;$('layers').replaceChildren();
 for(const part of sorted(doc.parts).reverse()){
  const b=document.createElement('button');b.className='layer'+(part.id===selected?' active':'')+(part.visible?'':' hidden');b.dataset.id=part.id;b.setAttribute('aria-label',labels[part.id]);
  const img=document.createElement('img');img.src='/source/'+part.asset;img.alt='';const name=document.createElement('span');name.className='name';name.textContent=labels[part.id];
  const eye=document.createElement('span');eye.className='eye';eye.textContent=part.visible?'◉':'○';eye.title=part.visible?'Đang hiện':'Đang ẩn';b.append(img,name,eye);b.onclick=e=>{if(e.target===eye)change(()=>part.visible=!part.visible);else{edit();selected=part.id;refresh();}};$('layers').append(b);
 }
 for(const b of $('faces').children)b.classList.toggle('active',doc.parts.find(p=>p.id==='head')?.asset===b.dataset.asset);
 draw();
}
for(const [asset,label] of [['head_front','Bình thường'],['head_turn','Nhìn nghiêng'],['head_scared','Sợ hãi'],['head_blink','Nhắm mắt']]){
 const b=document.createElement('button');b.dataset.asset=asset;b.innerHTML=`<img src="/source/${asset}" alt="">${label}`;b.onclick=()=>{const head=doc.parts.find(p=>p.id==='head');if(!head)return notice('Bản nhập không có đầu để đổi biểu cảm.',true);change(()=>{head.asset=asset;selected='head';});};$('faces').append(b);
}
function pointer(e){const r=canvas.getBoundingClientRect(),x=(e.clientX-r.left)/r.width*canvas.width,y=(e.clientY-r.top)/r.height*canvas.height;return {x:(x-canvas.width/2)/zoom+canvas.width/2,y:(y-canvas.height/2)/zoom+canvas.height/2};}
canvas.addEventListener('pointerdown',e=>{
 if(e.button!==0)return;if(preview!=='edit'){edit();draw();}canvas.focus();const pos=pointer(e),current=selectedPart();
 if(mode==='move'&&current.visible){
  const rot=worldPoint(current,current.width/2,-28/zoom);
  if(Math.hypot(pos.x-rot.x,pos.y-rot.y)<12/zoom){checkpoint();drag={kind:'rotate',angle:Math.atan2(pos.y-current.y,pos.x-current.x),before:clone(current)};canvas.setPointerCapture(e.pointerId);return;}
  for(const [u,v] of [[0,0],[1,0],[0,1],[1,1]]){const c=worldPoint(current,u*current.width,v*current.height);
   if(Math.hypot(pos.x-c.x,pos.y-c.y)<10/zoom){checkpoint();drag={kind:'resize',u,v,before:clone(current)};canvas.setPointerCapture(e.pointerId);return;}}
 }
 if(mode==='pivot'&&current.visible){const lp=localPoint(current,pos.x,pos.y);if(lp.x>=0&&lp.x<=current.width&&lp.y>=0&&lp.y<=current.height){checkpoint();drag={kind:'pivot',before:clone(current)};canvas.setPointerCapture(e.pointerId);return;}}
 const hit=sorted(doc.parts).reverse().find(p=>{if(!p.visible)return false;const t=localPoint(p,pos.x,pos.y);if(t.x<0||t.y<0||t.x>p.width||t.y>p.height)return false;
  const img=images[p.asset];if(!img)return false;const sample=document.createElement('canvas');sample.width=1;sample.height=1;const sc=sample.getContext('2d');sc.drawImage(img,t.x/p.width*img.width,t.y/p.height*img.height,1,1,0,0,1,1);return sc.getImageData(0,0,1,1).data[3]>20;});
 if(hit){selected=hit.id;checkpoint();drag={kind:'move',x:pos.x,y:pos.y,before:clone(hit)};canvas.setPointerCapture(e.pointerId);refresh();}
});
canvas.addEventListener('pointermove',e=>{if(!drag)return;const p=selectedPart(),pos=pointer(e);
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
$('move').onclick=()=>{mode='move';$('move').classList.add('active');$('pivot').classList.remove('active');$('mode-note').textContent='Kéo mảnh để chỉnh vị trí';};
$('pivot').onclick=()=>{mode='pivot';$('pivot').classList.add('active');$('move').classList.remove('active');$('mode-note').textContent='Chọn mảnh bên trái, kéo trên ảnh để đặt điểm xoay';};
$('undo').onclick=()=>{if(!undo.length)return;edit();redo.push(clone(doc));doc=undo.pop();persist();refresh();};
$('redo').onclick=()=>{if(!redo.length)return;edit();undo.push(clone(doc));doc=redo.pop();persist();refresh();};
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
try{await Promise.all([...assets.map(key=>image(key,'/source/'+key)),image('background','/source/background')]);refresh();status('Bản nháp tự lưu trên trình duyệt');await listSaves();}catch(e){notice('Không tải được ảnh hoặc danh sách bản lưu. Kiểm tra máy chủ rồi tải lại trang. '+e.message,true);}
