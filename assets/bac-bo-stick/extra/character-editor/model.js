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
  bend('l',Math.sin(phase)*12,5);bend('r',-Math.sin(phase)*12,-5);
  for(const [side,sign] of [['l',1],['r',-1]]){
   const thigh=get('thigh_'+side),shin=get('shin_'+side),foot=get('foot_'+side);if(!thigh||!shin||!foot)continue;
   const knee=localPoint(thigh,shin.x,shin.y),ankle=localPoint(shin,foot.x,foot.y),swing=Math.sin(phase)*sign*18;
   thigh.rotation+=swing;Object.assign(shin,worldPoint(thigh,knee.x,knee.y));shin.rotation+=swing+Math.max(0,Math.sin(phase)*sign)*24;Object.assign(foot,worldPoint(shin,ankle.x,ankle.y));
  }
 }
 return doc;
}
