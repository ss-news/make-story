"""Build editable stick-character parts from approved Stung Treng model sheets.
Run from repository root with .venv/bin/python. Does not edit storyvid or scenes.
"""
import json, math, copy
from pathlib import Path
ROOT=Path(__file__).resolve().parents[4]
E=ROOT/'assets/bac-bo-stick/extra'
INK='#17191a'
BASE=json.loads((ROOT/'assets/bac-bo-stick/characters/young_man/rig.json').read_text())
RUNTIME=['neutral','happy','scared','surprised','sad','angry','smirk']
EXTRA=['worried','terrified','crying','pleading','suspicious','exhausted','determined','embarrassed','blushing','shy_happy','sad_blush','relieved','laughing','blank','shadowed']
ALL=RUNTIME+EXTRA
# IDs specific to this production never replace base-pack characters.
PEOPLE=[
 ('stung_narrator','Narrator','young',False,1.,'side','#d0b994','round','flashlight'),
 ('stung_bay','Bay','middle',False,1.02,'receding','#727453','broad','none'),
 ('stung_luc','Luc','young',False,.98,'fringe','#45616a','narrow','none'),
 ('stung_tung','Tung','young',False,1.,'tousled','#88624a','angular','bag'),
 ('stung_sophal','Sophal','middle',False,1.,'neat','#45616a','oval','flashlight'),
 ('stung_vanna','Vanna','young',False,.98,'curly','#727453','round','scarf'),
 ('stung_foreman','Foreman','middle',False,1.02,'side','#a18d65','broad','bag'),
 ('stung_mr_chan','Mr Chan','elder',False,.94,'gray','#685042','narrow','none'),
 ('stung_mrs_chan','Mrs Chan','elder',True,.92,'bun','#45616a','oval','none'),
 ('legless_ghost_woman','The Woman','young',True,.98,'long','#795b45','round','none'),
 ('kneeling_ghost_woman','Kneeling Woman','middle',True,.96,'veil','#3d4142','oval','none'),
 ('stung_ghost_boy','Boy','child',False,.76,'tousled','#88624a','round','none'),
 ('fanged_ghost_child','Small Child','child',False,.58,'long_veil','#383d40','narrow','none')]
NPC=[
 ('stung_npc_man_round','NPC man round','middle',False,1.,'receding','#6d7160','broad','none'),
 ('stung_npc_man_thin','NPC man thin','young',False,.98,'fringe','#6b7680','narrow','none'),
 ('stung_npc_woman_long','NPC woman long hair','young',True,.95,'long','#927b75','oval','none'),
 ('stung_npc_woman_bun','NPC woman bun','middle',True,.96,'bun','#687566','round','none'),
 ('stung_npc_elder_man','NPC elder man','elder',False,.92,'gray','#7b6e5e','angular','none'),
 ('stung_npc_elder_woman','NPC elder woman','elder',True,.90,'bun','#6d717e','narrow','none'),
 ('stung_npc_boy','NPC boy','child',False,.70,'neat','#78816a','round','none'),
 ('stung_npc_girl','NPC girl','child',True,.67,'short_bob','#887783','oval','none')]
def p(d,fill='none',stroke=INK,w=4,attrs=''):return f'<path d="{d}" fill="{fill}" stroke="{stroke}" stroke-width="{w}" {attrs}/>'
def el(x,y,rx,ry,fill,stroke='none',w=4,attrs=''):return f'<ellipse cx="{x}" cy="{y}" rx="{rx}" ry="{ry}" fill="{fill}" stroke="{stroke}" stroke-width="{w}" {attrs}/>'
def rect(x,y,w,h,f,stroke=INK):return f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="{f}" stroke="{stroke}" stroke-width="4"/>'
def wrap(body,box='-140 -150 280 330'):return f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{box}"><g stroke-linecap="round" stroke-linejoin="round">{body}</g></svg>\n'
def face_shape(shape):
 if shape=='broad':return p('M-89 -22Q-91 -94 0 -96Q91 -92 89 -18L84 34Q68 89 0 91Q-72 86 -86 33Z','#fff')
 if shape=='narrow':return p('M-76 -25Q-80 -91 0 -94Q80 -90 77 -22L66 41Q43 91 0 94Q-46 87 -68 38Z','#fff')
 if shape=='angular':return p('M-85 -29Q-79 -92 0 -93Q82 -90 85 -25L75 40 35 87 -32 87 -77 36Z','#fff')
 if shape=='oval':return el(0,0,82,96,'#fff',INK)
 return el(0,0,89,91,'#fff',INK)
def hair(style):
 back='';front=''
 if style in ['long','long_veil','veil']:
  back=p('M-88 -30Q-100 -108 0 -109Q98 -110 89 -25L105 206 74 192 54 227 36 186H-46L-66 220 -99 204Z','#232426')
  front=p('M-88 -25Q-95 -106 0 -107Q94 -103 89 -25L73 46 62 -27 17 -64Q-18 -30 -81 -12Z','#232426')
  if style=='long_veil':front=p('M-89 -22Q-94 -106 0 -109Q97 -105 90 -17L85 148 54 167 34 65 21 -12 4 -60 -14 3 -34 79 -48 167 -83 153Z','#202224')
  if style=='veil':front=p('M-86 -25Q-94 -109 0 -111Q96 -107 90 -20L104 151 75 143 55 166 33 144 11 167 -14 148 -38 164 -63 142 -91 160Z','#202224')
 elif style=='bun':
  back=el(-68,-43,38,39,'#4d4f50',INK)
  front=p('M-84 -12Q-99 -90 -9 -103Q78 -113 86 -27L65 -13 32 -60Q-12 -29 -84 -12Z','#535557')
 elif style=='curly':
  front=p('M-84 -10Q-110 -25 -90 -49Q-108 -73 -76 -80Q-78 -111 -44 -101Q-21 -130 1 -104Q29 -124 46 -96Q79 -109 82 -78Q113 -69 91 -43Q109 -16 78 -5L61 -30 40 -21 18 -42 -3 -25 -27 -44 -47 -23 -66 -34Z','#282b2b')
 elif style=='receding':front=p('M-86 -5Q-100 -46 -73 -73L-51 -65 -39 -82 29 -82 44 -64 75 -75Q99 -39 85 -7L65 -19 63 -51 -61 -50 -65 -13Z','#292d2d')
 elif style=='fringe':front=p('M-87 -4Q-101 -96 -9 -103Q77 -111 90 -20L65 -28 52 -51 38 -28 24 -49 9 -27 -8 -46 -27 -28 -43 -44 -62 -21Z','#282b2b')
 elif style=='tousled':front=p('M-89 -5L-95 -47 -78 -66 -91 -76 -54 -80 -44 -104 -21 -95 1 -117 12 -98 48 -105 44 -87 83 -82 72 -66 96 -47 83 -1 66 -33 44 -47 26 -25 26 -51 -7 -30 -28 -47 -66 -20Z','#242829')
 elif style=='gray':front=p('M-84 -10Q-95 -80 -30 -95L-11 -108 27 -95 54 -96 82 -61 87 -9 66 -27 49 -49 18 -35 21 -58 -9 -44 -37 -50 -63 -24Z','#65696b')
 elif style=='short_bob':
  back=p('M-87 -26Q-98 -108 0 -106Q100 -99 88 -15L95 101 -93 101Z','#2a2c2d')
  front=p('M-87 -23Q-89 -104 0 -106Q91 -102 87 -24L47 -34 11 -58 -25 -30Z','#2a2c2d')
 elif style=='neat':front=p('M-86 -4Q-97 -94 -12 -101Q74 -110 88 -23L65 -14 44 -52Q1 -26 -70 -28L-69 -1Z','#282d2f')
 else:front=p('M-87 -5Q-103 -82 -32 -96L-4 -110 16 -100Q78 -104 90 -28L64 -14 43 -52Q4 -20 -22 -22L-8 -48Q-42 -20 -70 -22L-70 -2Z','#24292b')
 return back,front

def features(exp,seed=0,npc=False,child=False,elder=False):
 spacing=25+(seed%3-1)*3
 eyes='';brows='';mouth='';y=9
 # Character identity remains distinct even at neutral.
 if exp in ['happy','shy_happy','relieved','laughing']:
  eyes=p(f'M{-spacing-9} 10q9 -11 18 0m{2*spacing-18} 0q9 -11 18 0',w=4)
 elif exp in ['sad','crying','pleading','sad_blush','exhausted']:
  eyes=el(-spacing,12,5,8,INK)+el(spacing,12,5,8,INK)
 elif exp in ['scared','terrified','surprised']:
  rr=11 if exp=='terrified' else 9
  eyes=el(-spacing,10,rr,rr+3,'#fff',INK,3)+el(spacing,10,rr,rr+3,'#fff',INK,3)+el(-spacing,10,3,5,INK)+el(spacing,10,3,5,INK)
 elif exp=='suspicious':eyes=p(f'M{-spacing-9} 8h18m{2*spacing-18} 0h18',w=5)
 elif exp=='blank':eyes=''
 else:eyes=el(-spacing,10,5+(seed%2),9,INK)+el(spacing,10,5+(seed%2),9,INK)
 if exp=='pleading':
  eyes=el(-spacing,8,7,10,INK)+el(spacing,8,7,10,INK)+el(-spacing-2,5,2,2,'#fff')+el(spacing-2,5,2,2,'#fff')
 if exp in ['sad','worried','crying','pleading','sad_blush','embarrassed','terrified']:
  brows=p(f'M{-spacing-12} -15l23 -10m{2*spacing-24} 0l23 10',w=4)
 elif exp in ['angry','determined','sinister']:
  brows=p(f'M{-spacing-12} -24l24 10m{2*spacing-24} 0l24 -10',w=5)
 elif exp in ['surprised','scared']:brows=p(f'M{-spacing-11} -23q11 -10 22 0m{2*spacing-22} 0q11 -10 22 0',w=4)
 elif exp=='smirk':brows=p(f'M{-spacing-11} -16l22 -5m{2*spacing-22} -8l22 9',w=4)
 elif exp not in ['blank','shadowed']:brows=p(f'M{-spacing-10} -17q10 -5 20 0m{2*spacing-20} 0q10 -5 20 0',w=3)
 if exp in ['happy','shy_happy','relieved']:mouth=p('M-16 47Q0 66 16 47',w=4)
 elif exp=='laughing':mouth=p('M-21 43Q0 90 21 43Z','#5e3030')+p('M-11 63q11 -9 22 0','#b77574','none')
 elif exp in ['sad','worried','crying','pleading','sad_blush','exhausted']:mouth=p('M-15 57Q0 42 15 57',w=4)
 elif exp in ['scared','terrified','surprised']:mouth=el(0,53,9 if exp=='surprised' else 14,12 if exp=='surprised' else 18,'#553b3c',INK,3)
 elif exp=='angry':mouth=p('M-16 54Q0 43 16 54L15 65H-15Z','#fff')
 elif exp=='determined':mouth=p('M-16 54h32',w=4)
 elif exp=='smirk':mouth=p('M-11 56q15 4 27 -10',w=4)
 else:mouth=p('M-11 55q11 2 22 0',w=3)
 if exp=='relieved':
  brows=p('M-35 -16h20m30 0h20',w=3)
  mouth=p('M-11 50q11 12 22 0',w=3)
 if exp in ['embarrassed','blushing','shy_happy','sad_blush']:
  eyes+=el(-49,35,17,9,'#d58c8b',attrs='opacity=".55"')+el(49,35,17,9,'#d58c8b',attrs='opacity=".55"')
  eyes+=p('M-60 32l5 8m6 -8l5 8m84 -8l5 8m6 -8l5 8',stroke='#b5696b',w=2)
 if exp=='crying':eyes+=p('M-29 23q-8 25 -5 47m63 -47q8 25 5 47',stroke='#6c9bad',w=7)
 if exp in ['worried','scared','terrified','embarrassed']:eyes+=p('M68 -12q-12 18 -5 24q15 9 5 -24Z','#8db0bc','none')
 if exp=='exhausted':eyes+=p(f'M{-spacing-10} 29h20m{2*spacing-20} 0h20',stroke='#8b9196',w=3)
 if exp=='shadowed':
  eyes=''.join(el(0,2,72-i*6,27-i*2,'#303336',attrs=f'opacity="{.06+i*.025}"') for i in range(7))+p('M2 19L-3 35 6 38',w=3)
  brows=''
 if npc and exp=='neutral':
  if seed%3==0:eyes='';brows=''
  elif seed%3==1:eyes,brows,_=features('shadowed',seed)
 if elder:eyes+=p('M-56 27l-10 8m122 -8l10 8M-56 42l-6 11m118 -11l6 11',stroke='#727574',w=2)
 return eyes,brows,mouth

def make(info,seed):
 id,label,age,female,scale,style,color,shape,accessory=info
 dest=E/'characters'/id;dest.mkdir(parents=True,exist_ok=True)
 rig=copy.deepcopy(BASE);rig['label']=label;rig['scale']=scale
 def part(name,body):
  (dest/(name+'.svg')).write_text(wrap(f'<g id="{id}_{name}">{body}</g>'))
 # Write all existing contract keys, including optional accessories.
 for name in rig['parts']:part(name,'')
 back,front=hair(style)
 head=face_shape(shape)
 if seed%3==2 and style not in ['veil','long_veil']:head+=p('M2 24L-2 35 5 38',w=2.5)
 if female and style=='bun':head+=p('M-65 25l-8 5m138 -5l8 5',stroke='#767979',w=2)
 part('head',head);part('hair_back',back);part('hair_front',front)
 part('neck',p('M-8 -6V25H8V-6Z','#fff'))
 width=49 if shape=='broad' else 40
 body=p(f'M-31 0Q-40 18 -{width} 140H{width}Q40 18 31 0Z',color)
 if female:body+=p('M-13 0Q0 20 13 0',w=3)
 else:body+=p('M-18 -1L-4 20 0 4 8 20 21 -1',w=3)
 body+=p('M0 17V134',w=2)
 for yy in range(30,130,21):body+=el(5,yy,1.8,1.8,INK)
 if id=='legless_ghost_woman' or female:
  body+=p('M-31 100h21v24h-21ZM12 100h21v24H12Z',w=2.5)
 else:body+=p('M-30 40h22v24h-22ZM11 40h21v24H11Z',w=2)
 part('torso',body)
 part('upper_arm',p('M0 0V68',w=7)+p('M-10 0L-13 34H13L10 0Z',color))
 part('forearm',p('M0 0V69',w=7))
 part('hand',el(0,5,7,9,INK))
 part('thigh',p('M-12 0L-13 78H13L12 0Z','#303234'))
 part('shin',p('M-12 0L-10 103H10L12 0Z','#303234'))
 part('foot',p('M-10 -6Q-15 2 -25 5Q-29 13 -19 14H12V-6Z',INK))
 if female and id not in ['legless_ghost_woman','fanged_ghost_child']:
  part('thigh',p('M0 0V78',w=7));part('shin',p('M0 0V103',w=7))
  body+=p('M-38 132L-48 257H48L38 132Z','#35383a')+p('M-32 153L26 231',w=2)
  part('torso',body)
 # Optional pieces are separate from clothes so the rig can reuse them.
 part('bag',p('M36 8L-40 147',stroke='#b09b72',w=12)+p('M-77 109L-40 115 -38 167 -82 162Z','#9b855f')+p('M-77 122l37 6',w=2))
 scarf=p('M-21 0Q0 19 22 0L31 18 17 29 18 100 -1 104 -5 32 -28 18Z','#b7a692')
 for y in range(22,100,9):scarf+=p(f'M-1 {y}H17',stroke='#71574e',w=2)
 scarf+=p('M3 26v73m8 -73v73',stroke='#71574e',w=2)
 part('scarf',scarf)
 part('flashlight',p('M-8 -13H9V21H-8Z','#4e5855')+p('M-13 -19H14V-6H-13Z','#767d72')+el(0,-18,11,4,'#d5d8c8',INK,2))
 torso_body=body
 for exp in ALL+['closed']:
  eyes,brows,mouth=features('neutral' if exp=='closed' else exp,seed,id.startswith('stung_npc'),age=='child',age=='elder')
  if exp=='closed':eyes=p('M-35 11q10 7 20 0m30 0q10 7 20 0',w=4)
  if id=='fanged_ghost_child':mouth+=p('M-17 48l6 26 6 -25m10 0l6 25 6 -26','#e6e3d4',INK,2)
  part('eyes_'+exp,eyes);part('brows_'+exp,brows)
  if exp!='closed':part('mouth_'+exp,mouth)
 for name,body in {
  'half':el(0,54,12,5,'#643e3e',INK,3),
  'open':el(0,54,13,15,'#643e3e',INK,3),
  'phoneme_a':el(0,54,14,18,'#643e3e',INK,3),
  'phoneme_e':p('M-18 48Q0 40 18 48L17 62Q0 68 -17 62Z','#643e3e'),
  'phoneme_o':el(0,54,8,12,'#643e3e',INK,3),
  'phoneme_m':p('M-13 54Q0 58 13 54',w=4),
  'phoneme_f':p('M-15 48h30l-3 12h-24Z','#fff')}.items():
  if id=='fanged_ghost_child':body+=p('M-17 48l6 26 6 -25m10 0l6 25 6 -26','#e6e3d4',INK,2)
  part('mouth_'+name,body)
 part('eyes_half_closed',p('M-36 8h22m28 0h22',w=4)+el(-25,12,4,4,INK)+el(25,12,4,4,INK))
 if id=='legless_ghost_woman':
  for name in ['thigh','shin','foot']:part(name,'')
  part('torso',torso_body+p('M-39 137l9 12 10 -9 12 12 11 -12 9 11 15 -14 9 11',stroke=color,w=6))
 if id=='kneeling_ghost_woman':
  # Bent silhouette uses the existing pivots, with each local artwork offset to the ground.
  part('head',p('M-60 250Q-75 194 -10 183Q52 176 63 243L58 283Q0 319 -56 280Z','#fff'))
  part('hair_back',p('M-84 225Q-88 150 -5 151Q85 157 83 232L106 403 -100 403Z','#252729'))
  # Cover most of the face, leaving a narrow side opening for readable lip and blink states.
  part('hair_front',p('M-84 227Q-88 153 -5 152Q86 157 82 234L99 404 64 410 30 391 9 409 -11 382 -28 330 -43 258 -48 403 -95 411Z M2 244L35 250 30 290 8 279Z','#252729',attrs='fill-rule="evenodd"'))
  part('neck','')
  part('torso',p('M-2 95Q43 37 94 85L126 161 83 221 -25 214Z','#464849')+p('M70 201q49 -16 72 30l-11 44H11q-30 -20 -2 -42Z','#343739'))
  for name in ['upper_arm','forearm','hand','thigh','shin','foot']:part(name,'')
  # Separate limb segments kept in additional pose parts for the low kneeling stance.
  part('pose_upper_arm',p('M0 0L8 65',w=7));part('pose_forearm',p('M0 0L-10 69',w=7));part('pose_hand',el(0,0,8,6,INK))
  # Two planted arms behind the veil; the required shared arm joints would otherwise rotate them upright.
  part('torso',p('M-2 95Q43 37 94 85L126 161 83 221 -25 214Z','#464849')+p('M70 201q49 -16 72 30l-11 44H11q-30 -20 -2 -42Z','#343739')+p('M36 118L24 206 9 276M66 138L67 218 50 276',w=7)+el(8,279,10,6,INK)+el(49,279,10,6,INK))
  for exp in ALL+['closed']:
   eyes,brows,mouth=features('neutral' if exp=='closed' else exp,seed)
   if exp=='closed':eyes=p('M-35 11h20m30 0h20',w=3)
   for kind,body2 in [('eyes',eyes),('brows',brows),('mouth',mouth)]:
    if kind=='mouth' and exp=='closed':continue
    part(kind+'_'+exp,f'<g transform="translate(12 245) scale(.45)">{body2}</g>')
  for state in ['half','open','phoneme_a','phoneme_e','phoneme_o','phoneme_m','phoneme_f']:
   part('mouth_'+state,f'<g transform="translate(12 245) scale(.45)">{el(0,54,12,6 if state=="half" else 14,"#643e3e",INK,3)}</g>')
 # Custom expression files are explicit source resources, not unknown scene enum values.
 available={x.stem:x.name for x in dest.glob('*.svg')}
 (dest/'face-library.json').write_text(json.dumps({'runtime_expressions':RUNTIME,'source_expressions':EXTRA,'phonemes':['a','e','o','m','f'],'parts':available},indent=2)+'\n')
 (dest/'rig.json').write_text(json.dumps(rig,ensure_ascii=False,indent=2)+'\n')
 return dict(id=id,label=label,female=female,age=age,scale=scale,skin='#ffffff',hair='#252729')

manifest=json.loads((E/'manifest.json').read_text())
for i,info in enumerate(PEOPLE+NPC):
 entry=make(info,i)
 manifest['characters']=[x for x in manifest['characters'] if x['id']!=entry['id']]+[entry]

FX={
 'stung_blush_cheeks':el(150,180,49,25,'#d78a88',attrs='opacity=".65"')+el(330,180,49,25,'#d78a88',attrs='opacity=".65"'),
 'stung_embarrassed_hatch':p('M120 155l18 42m15 -42l18 42m138 -42l18 42m15 -42l18 42',stroke='#ba7077',w=7),
 'stung_tear_drop':p('M240 60Q110 231 190 281Q289 337 305 236Q305 193 240 60Z','#8bb5c9',INK,4),
 'stung_tear_streams':p('M153 85q-27 95 -9 180m190 -180q27 95 9 180',stroke='#8bb5c9',w=23),
 'stung_sweat_drop':p('M250 65Q165 202 191 237Q239 288 279 234Q303 195 250 65Z','#a3c7d6',INK,4),
 'stung_sparkle_star':p('M240 50L267 145 345 180 267 211 240 310 210 211 135 180 211 145Z','#f6d55d','#dbb441',6),
 'stung_anger_mark':p('M180 95q65 2 64 65m55 -65q-65 2 -64 65m-55 67q65 -2 64 -65m55 65q-65 -2 -64 -65',stroke='#b74b48',w=12),
 'stung_shadow_eyes':''.join(el(240,180,180-i*12,70-i*4,'#282b2f',attrs=f'opacity="{.04+i*.017}"') for i in range(9)),
 'stung_shock_lines':p('M115 75L80 25M240 70V10M365 75l35 -50M105 165l-55 -15m325 15l55 -15',stroke='#d0c29c',w=12),
 'stung_tremble_lines':p('M105 80l-17 30 17 30 -17 30 17 30 -17 30M375 80l17 30 -17 30 17 30 -17 30 17 30',stroke='#7e8e97',w=8),
 'stung_heart_pop':p('M240 285L140 191Q65 100 155 77Q218 65 240 129Q264 65 325 77Q415 100 340 191Z','#be7078','#744b57',5),
 'stung_laugh_tears':p('M140 95Q55 165 108 195Q159 220 140 95Z','#8bb5c9')+p('M340 95Q425 165 372 195Q321 220 340 95Z','#8bb5c9')}
for id,body in FX.items():
 folder=E/'effects';folder.mkdir(exist_ok=True)
 (folder/f'{id}.svg').write_text(wrap(body,'0 0 480 360'))
 manifest['assets']=[x for x in manifest['assets'] if x['id']!=id]+[dict(id=id,label=id.replace('stung_','').replace('_',' '),group='effects',svg=f'effects/{id}.svg')]
(E/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
meta={'format':'stung-character-source/1','approved_reference':'output/stung_treng/concepts/people-v1.png + ghosts-v1.png','characters':[dict(id=x[0],name=x[1],default_accessory=x[8]) for x in PEOPLE],'npcs':[x[0] for x in NPC],'runtime_expressions':RUNTIME,'source_expressions':EXTRA,'effects':list(FX),'note':'Source-only expressions and effects are not automatically usable by the current scenes/1 renderer. No core code changes.'}
(E/'stung-character-library.json').write_text(json.dumps(meta,ensure_ascii=False,indent=2)+'\n')
print(f'Built {len(PEOPLE)} story characters + {len(NPC)} NPCs; {len(ALL)} expressions; {len(FX)} effects.')
