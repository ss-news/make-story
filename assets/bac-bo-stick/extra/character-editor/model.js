export const labels={head:'Đầu / biểu cảm',torso:'Thân áo',upper_arm_l:'Bắp tay bên trái',upper_arm_r:'Bắp tay bên phải',forearm_l:'Cẳng tay bên trái',forearm_r:'Cẳng tay bên phải',hand_l:'Bàn tay bên trái',hand_r:'Bàn tay bên phải',thigh_l:'Đùi bên trái',thigh_r:'Đùi bên phải',shin_l:'Cẳng chân bên trái',shin_r:'Cẳng chân bên phải',foot_l:'Bàn chân bên trái',foot_r:'Bàn chân bên phải',flashlight:'Đèn pin',shoulder_l:'Miếng vai bên trái',shoulder_r:'Miếng vai bên phải'};
export const assets=['head_front','head_turn','head_scared','head_blink',...Object.keys(labels).filter(k=>k!=='head')];
export const clone=v=>JSON.parse(JSON.stringify(v));
export function defaults(){
 const parts=[];const s=210,ox=500,oy=735;
 function add(id,x,y,w,h,z,pivotX=.5,pivotY=.5,rotation=0,visible=true){parts.push({id,asset:id==='head'?'head_front':id,x:ox+x*s,y:oy-y*s,width:w*s,height:h*s,z,pivotX,pivotY,rotation,visible});}
 for(const [side,x] of [['l',-.25],['r',.25]]){
  const hx=side==='l'?-.13:.13;
  add('thigh_'+side,hx,.98,.18,.52,2,.5,.035,-7.7);
  add('shin_'+side,hx+.065,.50,.155,.475,1,.5,.035,8.4);
  add('foot_'+side,hx+.035,.055,.255,.12,3);
  add('upper_arm_'+side,x,1.48,.20,.365,4,.5,.045,side==='l'?8.9:-8.9);
  const ex=x+(side==='l'?-.051:.051),ey=1.154;
  add('forearm_'+side,ex,ey,.048,.345,7,.5,.05,side==='l'?8.6:-8.6);
  add('hand_'+side,ex+(side==='l'?-.046:.046),.847,.075,.105,9);
  add('shoulder_'+side,x,1.48,.20,.20,6,.5,.5,0,false);
 }
 add('torso',0,1.24,.66,.80,5);
 add('head',0,2.13,1.10,1.08,12);
 add('flashlight',.422,.847,.33,.16,8,.25,.5,0,false);
 return {format:'character-layout/1',source:'human-action-trial-v1',title:'Nhân vật áo kem',canvas:{width:1000,height:800},parts};
}
export function validate(doc){
 if(!doc||doc.format!=='character-layout/1'||doc.source!=='human-action-trial-v1')throw Error('Sai định dạng hoặc bộ nhân vật.');
 const num=(v,min,max)=>typeof v==='number'&&Number.isFinite(v)&&v>=min&&v<=max;
 if(!doc.canvas||!['width','height'].every(k=>num(doc.canvas[k],100,4096)))throw Error('Kích thước khung không hợp lệ.');
 if(!Array.isArray(doc.parts)||!doc.parts.length||doc.parts.length>40)throw Error('Danh sách bộ phận không hợp lệ.');
 const ids=new Set();
 for(const p of doc.parts){
  if(!p||typeof p.id!=='string'||!Object.hasOwn(labels,p.id)||ids.has(p.id)||!assets.includes(p.asset))throw Error('Mã bộ phận bị trùng hoặc không được hỗ trợ.');ids.add(p.id);
  for(const k of ['x','y'])if(!num(p[k],-8192,8192))throw Error('Vị trí ngoài giới hạn.');
  for(const k of ['width','height'])if(!num(p[k],1,4096))throw Error('Kích thước ngoài giới hạn.');
  for(const k of ['pivotX','pivotY'])if(!num(p[k],0,1))throw Error('Điểm xoay phải nằm trong ảnh.');
  if(!num(p.rotation,-360,360)||!num(p.z,-100,100)||typeof p.visible!=='boolean')throw Error('Góc xoay hoặc thứ tự lớp không hợp lệ.');
 }
 if(doc.title!==undefined&&(typeof doc.title!=='string'||doc.title.length>160))throw Error('Tên cấu hình quá dài.');
 return clone(doc);
}
export function localPoint(p,x,y){const a=-p.rotation*Math.PI/180,c=Math.cos(a),s=Math.sin(a),dx=x-p.x,dy=y-p.y;return {x:c*dx-s*dy+p.pivotX*p.width,y:s*dx+c*dy+p.pivotY*p.height};}
export function worldPoint(p,x,y){const a=p.rotation*Math.PI/180,c=Math.cos(a),s=Math.sin(a),dx=x-p.pivotX*p.width,dy=y-p.pivotY*p.height;return {x:p.x+c*dx-s*dy,y:p.y+s*dx+c*dy};}
export function movePivot(p,px,py){const world=worldPoint(p,px*p.width,py*p.height);p.x=world.x;p.y=world.y;p.pivotX=px;p.pivotY=py;}
// Independent layout presets, deliberately no implicit skeletal or Blender animation.
export function posed(document,name,phase=0){
 const doc=clone(document);if(name==='edit')return doc;
 const get=id=>doc.parts.find(p=>p.id===id);
 const bend=(side,angle,elbow)=>{
  const upper=get('upper_arm_'+side),fore=get('forearm_'+side),hand=get('hand_'+side);
  if(!upper||!fore||!hand)return;
  const oldEnd=localPoint(upper,fore.x,fore.y),oldHand=localPoint(fore,hand.x,hand.y);
  upper.rotation+=angle;const end=worldPoint(upper,oldEnd.x,oldEnd.y);fore.x=end.x;fore.y=end.y;fore.rotation+=angle+elbow;
  const tip=worldPoint(fore,oldHand.x,oldHand.y);hand.x=tip.x;hand.y=tip.y;hand.rotation+=angle+elbow;
 };
 if(name==='aim'){bend('r',-52,-28);const f=get('flashlight'),h=get('hand_r');if(f&&h){f.visible=true;f.x=h.x;f.y=h.y;f.rotation=0;}const head=get('head');if(head)head.asset='head_turn';}
 if(name==='scared'){bend('l',65,45);bend('r',-65,-45);const head=get('head');if(head)head.asset='head_scared';}
 if(name==='walk'){
  // Side walk in place toward the viewer's left, where head_turn looks. Rotation is clockwise, so f=-1 makes a forward (left) swing positive.
  const f=-1,bottom=p=>Math.max(...[[0,p.height],[p.width,p.height]].map(([x,y])=>worldPoint(p,x,y).y));
  const feet=['foot_l','foot_r'].map(get).filter(Boolean),ground=feet.length?Math.max(...feet.map(bottom)):null;
  const head=get('head');if(head)head.asset='head_turn';
  const hips=['thigh_l','thigh_r'].map(get).filter(Boolean),hipX=hips.reduce((a,p)=>a+p.x,0)/(hips.length||1);
  for(const [side,offset] of [['l',0],['r',Math.PI]]){
   const t=phase+offset,hip=22*Math.sin(t),knee=45*Math.max(0,Math.cos(t))**2+4;
   const arm=-16*Math.sin(t);bend(side,-f*arm,-f*(.6*Math.max(0,arm)+4));
   const thigh=get('thigh_'+side),shin=get('shin_'+side),foot=get('foot_'+side);if(!thigh||!shin||!foot)continue;
   const kneeAt=localPoint(thigh,shin.x,shin.y),ankleAt=localPoint(shin,foot.x,foot.y);
   thigh.x+=(hipX-thigh.x)*.7;thigh.rotation-=f*hip;
   Object.assign(shin,worldPoint(thigh,kneeAt.x,kneeAt.y));shin.rotation-=f*(hip-knee);
   Object.assign(foot,worldPoint(shin,ankleAt.x,ankleAt.y));foot.rotation+=f*.3*knee;
   // foot_l points its toe right, foot_r left; both feet face the walking direction.
   const toward=f>0?'foot_l':'foot_r';if(foot.asset!==toward&&foot.asset.startsWith('foot_')){foot.asset=toward;foot.pivotX=1-foot.pivotX;}
  }
  // Keep the lowest foot planted on the ground line of the edit layout.
  if(ground!==null){const dy=ground-Math.max(...feet.map(bottom));for(const p of doc.parts)p.y+=dy;}
 }
 return doc;
}
// Front-to-back list order is the reverse of the stable ascending render order.
export function reorderLayers(document,sourceId,targetId,before=true){
 const result=clone(document);if(sourceId===targetId)return result;
 const order=[...result.parts].sort((a,b)=>a.z-b.z).reverse();
 const source=order.find(p=>p.id===sourceId),target=order.find(p=>p.id===targetId);
 if(!source||!target)throw Error('Không tìm thấy bộ phận để xếp lớp.');
 order.splice(order.indexOf(source),1);order.splice(order.indexOf(target)+(before?0:1),0,source);
 order.forEach((p,i)=>p.z=order.length-1-i);
 return result;
}
export function translateParts(document,ids,dx,dy){
 if(!Number.isFinite(dx)||!Number.isFinite(dy))throw Error('Độ dịch chuyển không hợp lệ.');
 const result=clone(document),wanted=new Set(ids),parts=result.parts.filter(p=>wanted.has(p.id));
 if(!parts.length||parts.length!==wanted.size)throw Error('Cụm có bộ phận không tồn tại.');
 dx=Math.max(Math.max(...parts.map(p=>-8192-p.x)),Math.min(Math.min(...parts.map(p=>8192-p.x)),dx));
 dy=Math.max(Math.max(...parts.map(p=>-8192-p.y)),Math.min(Math.min(...parts.map(p=>8192-p.y)),dy));
 for(const part of parts){part.x+=dx;part.y+=dy;}return result;
}
