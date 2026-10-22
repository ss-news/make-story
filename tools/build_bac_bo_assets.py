"""Editable, deterministic SVG source for the approved northern stick cartoon pack."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from storyvid.character_catalog import PRESETS

ROOT = Path(__file__).resolve().parents[1]
PACK = ROOT / 'assets' / 'bac-bo-stick'
INK = '#24211f'
CATALOG = []


def svg(body, box='0 0 480 640', width=None, height=None):
    sizes = f' width="{width}" height="{height}"' if width else ''
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{box}"{sizes}>'
            f'<g stroke="{INK}" stroke-width="4" stroke-linecap="round" stroke-linejoin="round">'
            f'{body}</g></svg>\n')


def path(d, fill='none', stroke=None, sw=None):
    return f'<path d="{d}" fill="{fill}"'+(f' stroke="{stroke}"' if stroke else '')+(f' stroke-width="{sw}"' if sw else '')+'/>'


def ellipse(x, y, rx, ry, fill='white', sw=None):
    return f'<ellipse cx="{x}" cy="{y}" rx="{rx}" ry="{ry}" fill="{fill}"'+(f' stroke-width="{sw}"' if sw else '')+'/>'


def save(group, key, label, body, box='0 0 480 360'):
    folder = PACK / group
    folder.mkdir(parents=True, exist_ok=True)
    file = folder / (key+'.svg')
    file.write_text(svg(body, box))
    CATALOG.append({'id':key, 'label':label, 'group':group, 'svg':str(file.relative_to(PACK)), 'viewBox':box})


def build_characters():
    for preset, info in PRESETS.items():
        female, age = info['female'], info['age']
        folder = PACK/'characters'/preset
        folder.mkdir(parents=True, exist_ok=True)
        parts = {
            'neck':path('M-7-9L-6 28M7-9L6 28','none'),
            'upper_arm':path('M0 0Q-3 31 0 68','none',sw=5),
            'forearm':path('M0 0Q3 33 0 69','none',sw=5),
            'hand':ellipse(0,4,5,6,'#fff',3),
            'thigh':path('M0 0Q-2 37 0 78','none',sw=5),
            'shin':path('M0 0Q3 47 0 103','none',sw=5),
            'foot':path('M0-2L-3 7Q-17 14-24 8Q-25 3-14 4L-4 2',INK,sw=3),
            'head':path('M-83-25Q-83-88-5-91Q77-96 85-31L84 21Q80 86 4 88Q-70 90-82 31Q-103 42-104 21Q-106 2-84 10Z','#fff',sw=4.5),
            'hair_back':'',
            'torso':path('M-30 0L-41 131Q0 137 42 130L31 0L13-4Q0 10-13-4Z','{{shirt}}')+path('M-9 3L0 21L9 3M0 23L1 126','none',sw=2.5),
            'bag':path('M-32 0L35 92','none','#c3a06d',7)+path('M17 81L54 87L49 126L14 121Z','#b99b6c'),
            'scarf':path('M-22 0Q0 18 23 0L26 12L10 25L18 78L2 82L-5 27L-25 13Z','#485f6a')+path('M-19 8Q0 23 19 8','none',sw=2),
            'flashlight':path('M-6-10H6V24H-6Z','#686f64')+path('M-11-23H11V-9H-11Z','#c8bc83'),
        }
        if female:
            # Black scarf wraps the white face, leaving eyes/mouth unobscured.
            parts['hair_back'] = path('M-85-30Q-97-98-7-107Q76-110 94-51L91 45L58 92L61 35L-66 15L-79 73L-95 38Z','#292728')
            parts['hair_front'] = path('M-83-30Q-32-76 4-100Q68-78 83-32L62-45L1-84L-52-39Z','#282626')+path('M79 35L106 73L79 66L95 96L62 76Z','#282626')
            parts['torso'] = path('M-31 0L-48 134L-8 133L0 76L8 133L48 134L31 0L13-4H-13Z','{{shirt}}')+path('M-13 0L0 60L13 0Z','#b65a45')+path('M-28 74Q0 87 29 75M-6 80L-15 128M5 80L16 127','none',sw=3)
            if age == 'child':
                parts['hair_back'] = path('M-73-15Q-117-3-104 54L-82 29M73-15Q117-3 104 54L82 29','#24211f')
                parts['hair_front'] = path('M-82-10Q-98-102-4-100Q86-106 86-11L64-39Q25-39-1-81Q-27-34-66-37Z','#24211f')+path('M-99 14L-82 17M82 17L99 14','none','#b65a45',7)
        else:
            parts['hair_front'] = path('M-82-18L-86-68L-60-72L-55-94L-31-85L-16-103L7-88L34-101L47-82L71-79L84-45L82-14L64-42L36-48L15-64L-12-43L-49-45Z','#272525')
            if age in ('elder','middle'):
                parts['hair_front'] = path('M-85-39L-93-67Q-18-107 67-86L84-54L81-32Q8-71-85-39Z','#343031')+path('M-87-56Q-6-91 72-69','none','#77716b',2.5)
                parts['head'] += path('M-15 43Q-5 33 0 41Q8 33 18 43','none',sw=3)
            if age == 'elder':
                parts['head'] += path('M-15 83Q-9 109 0 115Q11 105 17 82','#e0dbd4',sw=2.5)+path('M-67 12L-76 16M67 12L76 16','none',sw=2)
        if age == 'elder' and female:
            parts['head'] += path('M-66 13L-75 17M66 13L75 17','none',sw=2)
            parts['hair_front'] += path('M-70-38Q-49-49-31-62M48-50L68-34','none','#c9c5bd',6)
            parts['hair_back'] += ellipse(74,-61,23,24,'#b7b4ad',3)
        if age == 'middle' and female:
            parts['hair_front'] = parts['hair_front'].replace('#282626','#414b50')
        for exp in ('neutral','happy','scared','surprised','sad','angry','smirk','closed'):
            eye, brow = '', ''
            for side in (-1,1):
                x = side*30
                if exp in ('scared','surprised'):
                    eye += ellipse(x,5,20,25,'#fff',3)+ellipse(x+(2 if side>0 else -2),7,5,8,INK,2)
                elif exp in ('happy','closed'):
                    eye += path(f'M{x-12} 7Q{x} {-10 if exp=="happy" else 16} {x+12} 7','none',sw=3.5)
                elif exp in ('angry','smirk'):
                    eye += path(f'M{x-16} -4L{x+15} 0Q{x+12} 22 {x-12} 14Z','#fff',sw=3)+ellipse(x+2,8,3,5,INK,2)
                else:
                    eye += ellipse(x,5,4,7,INK,2)
                by = -37 if exp in ('scared','surprised') else -22
                tilt = -side*10 if exp=='angry' else side*9 if exp=='sad' else 0
                brow += path(f'M{x-13} {by-tilt}Q{x} {by-7} {x+13} {by+tilt}','none',sw=3.5)
            parts['eyes_'+exp], parts['brows_'+exp] = eye, brow
        mouths = {
            'neutral':path('M-12 48Q0 53 13 47','none',sw=3),
            'happy':path('M-23 40Q0 51 24 39Q23 73 0 73Q-18 73-23 40Z',INK)+path('M-11 67Q0 53 13 66','#c96d5c',sw=2),
            'scared':path('M-19 65Q-15 28 2 31Q17 34 22 65Z',INK)+path('M-10 62Q0 51 12 62','#c96d5c',sw=2),
            'surprised':ellipse(0,51,15,21,INK,3),
            'sad':path('M-19 56Q0 35 20 55','none',sw=3.5),
            'angry':path('M-19 44L20 41L17 61L-19 60Z','#fff',sw=3)+path('M-17 51L17 50','none',sw=2),
            'smirk':path('M-17 53Q12 60 24 42','none',sw=3.5),
            'half':ellipse(0,51,12,8,INK,3),
            'open':ellipse(0,51,17,21,INK,3)+path('M-9 63Q0 53 10 63','#c96d5c',sw=2),
        }
        parts.update({'mouth_'+key:body for key,body in mouths.items()})
        metadata = {}
        for key, body in parts.items():
            (folder/(key+'.svg')).write_text(svg(body,'-140 -150 280 330'))
            metadata[key] = {'file':key+'.svg','pivot':[0,0]}
        rig = {'viewBox':[0,0,400,640], 'scale':info['scale'], 'head_scale':1.02 if age=='child' else 1,
               'parts':metadata, 'anchors':{'head':[200,174], 'neck':[200,263], 'torso':[200,280],
               'shoulder_L':[166,294], 'shoulder_R':[234,294], 'hip_L':[181,409], 'hip_R':[219,409]},
               'lengths':{'upper_arm':68,'forearm':69,'thigh':78,'shin':103}, 'face':{'eye_y':5,'mouth_y':51},
               'style':'bac-bo-stick-10', 'label':info['label']}
        (folder/'rig.json').write_text(json.dumps(rig,ensure_ascii=False,indent=2)+'\n')


def face(x,y,scared=False):
    eyes = ''.join(ellipse(x+dx,y,8 if scared else 3,10 if scared else 4,'white' if scared else INK,2) for dx in (-15,15))
    if scared:
        eyes += ''.join(ellipse(x+dx,y,2.5,4,INK,1) for dx in (-15,15))
    return eyes + (ellipse(x,y+24,9,13,'#a7493e',2.5) if scared else path(f'M{x-11} {y+20}Q{x} {y+31} {x+12} {y+19}','none',sw=2.5))


def build_animals():
    for key,label,color,horns in [('buffalo','Trâu','#68676a',True),('cow','Bò','#bd8b57',True),('pig','Lợn','#e7b5ab',False),('dog','Chó','#c69a69',False),('cat','Mèo','#d3b989',False)]:
        is_pet = key in ('dog','cat')
        body = ellipse(254,202,108,66,color)+path('M180 238L177 299L192 299M221 250L218 301L234 301M294 250L299 299L314 299M335 235L346 293L360 293','none',sw=5)
        body += path('M352 191Q405 143 385 132','none',sw=5)
        if key=='pig':
            body = body.replace('M352 191Q405 143 385 132','M352 191Q400 170 388 152Q372 137 374 159Q375 177 394 169')
        body += ellipse(148,181,72,65,color)
        if horns:
            body += path('M104 140Q49 146 56 96Q66 121 115 119Z','#c4bca8')+path('M181 137Q236 139 233 90Q222 118 174 117Z','#c4bca8')
            body += ellipse(93,163,20,9,color)+ellipse(207,161,20,9,color)
        elif key=='cat':
            body += path('M94 142L97 94L130 120M169 118L201 92L204 147',color)
            body += path('M94 198L57 190M94 207L57 209M199 196L235 184M200 206L237 205','none',sw=2)
        elif key=='dog':
            body += path('M100 135Q61 127 81 195L101 179M193 137Q228 126 218 187L196 179',color)
        else:
            body += path('M104 132L85 102L128 122M176 121L210 101L199 142',color)
            body += ellipse(147,207,30,19,'#d8948e',2)+ellipse(136,207,3,5,INK,1)+ellipse(158,207,3,5,INK,1)
        body += face(148,173,key=='buffalo')
        save('animals',key,label,body)
    for key,label,color in [('rooster','Gà trống','#b06a43'),('hen','Gà mái','#c29462'),('duck','Vịt','#f5eee2')]:
        body=ellipse(242,207,73,52,color)+path('M183 202L140 157L158 222Z',color)+path('M229 251L226 294L208 299M258 251L263 294L283 299','none','#aa713c',4)
        body+=path('M272 186Q259 142 283 122Q320 113 326 145L316 202Z',color)+ellipse(300,144,28,30,color)
        body+=path('M326 140L360 150L326 160Z','#d79844')+ellipse(305,139,4,6,INK,2)
        if key=='rooster':
            body+=path('M281 118Q269 92 286 98Q301 76 306 99Q325 84 322 119Z','#b64e3e')+path('M186 185Q127 105 130 177Q104 129 118 204','none','#456568',12)
        body+=path('M214 208Q235 183 262 209Q239 237 214 208','none',sw=2.5)
        save('animals',key,label,body)
    save('animals','stork','Cò',path('M240 212L230 302L205 308M256 214L270 300L293 306','none',sw=4)+ellipse(235,187,63,36,'#fff')+path('M263 166Q295 151 288 101Q286 74 307 75Q334 75 326 101Q317 140 304 181L280 207Z','#fff')+path('M324 87L382 106L323 99Z','#c6924e')+ellipse(312,86,3,4,INK,1)+path('M184 187Q227 156 255 195L204 216Z','#363635'))


def build_props():
    props={
        'conical_hat':('Nón lá',path('M78 214L241 77L404 214Q237 278 78 214Z','#e4d1a0')+path('M83 215Q236 188 400 215M239 82L153 231M243 83L321 231','none','#a38d63',2)+path('M159 242Q238 322 322 241','none','#a65b4c',4)),
        'flat_palm_hat':('Nón quai thao',ellipse(240,160,172,35,'#d7bf87')+path('M68 160L70 188Q240 233 410 188V160','#dec996')+path('M127 201Q122 322 228 304M354 202Q358 322 252 304','none','#9a4543',7)),
        'flute':('Sáo trúc',path('M83 220L388 109L395 129L90 240Z','#c59b58')+''.join(ellipse(144+i*35,210-i*13,3,4,INK,1) for i in range(6))),
        'carrying_pole':('Quang gánh',path('M65 116Q242 77 415 115','none','#b5915e',9)+path('M94 112L75 255M120 107L141 253M359 108L339 254M388 113L410 254','none',sw=2.5)+path('M50 246L166 246L153 293Q105 308 64 292Z','#ba9667')+path('M316 246L432 246L419 293Q368 308 330 292Z','#ba9667')),
        'basket':('Thúng tre',ellipse(240,139,123,32,'#bb9665')+path('M117 139L136 260Q240 312 344 260L363 139Q240 193 117 139Z','#d0b17d')+path('M156 164L171 274M205 177L210 287M260 178L258 287M315 166L304 276M130 198Q242 240 353 198M135 236Q240 277 346 236','none','#9b7a50',2)),
        'winnowing_tray':('Nia tre',ellipse(240,184,159,108,'#d5ba85')+ellipse(240,184,145,95,'#e0c99a',2)+''.join(path(f'M{110+i*35} 115L{175+i*27} 267','none','#b09362',1.5) for i in range(7))+''.join(path(f'M109 {130+i*24}L372 {150+i*20}','none','#b09362',1.5) for i in range(6))),
        'water_jar':('Chum nước',path('M184 102Q160 94 170 80H310Q320 94 296 102L302 125Q358 161 336 260Q331 288 240 293Q149 288 144 260Q122 161 178 125Z','#9e6e50')+ellipse(240,83,70,12,'#4f453c',3)+path('M171 169Q155 210 173 251','none','#c39774',4)),
        'oil_lamp':('Đèn dầu',path('M197 271L205 227H275L283 271Z','#ad8154')+path('M210 224Q186 169 202 109L196 91H284L278 109Q294 169 270 224Z','#eff2ec')+path('M239 212Q211 178 241 142Q269 185 249 211Z','#efbd56')+path('M203 230H276M191 276H290','none',sw=6)),
        'hoe':('Cuốc',path('M145 298L295 68','none','#b48d58',11)+path('M264 82L329 113L292 173L236 132Z','#7d8178')),
        'sickle':('Liềm',path('M139 289L213 189','none','#b48d58',14)+path('M206 192Q179 79 318 70Q235 111 238 195Z','#9caaa3')),
        'broom':('Chổi rơm',path('M300 62L214 208','none','#9e7b4e',9)+path('M214 191L127 273Q164 315 224 304L241 209Z','#d0ad66')+path('M211 216L160 281M221 218L188 292M231 221L216 296','none','#9f814c',2)+path('M197 219L236 239','none','#6c6748',7)),
        'bamboo_fence':('Hàng rào tre', ''.join(path(f'M{x} 95L{x+8} 288','none','#a99968',12) for x in (70,125,180,235,290,345,400))+path('M54 147L427 169M59 233L430 247','none','#a99968',10)+''.join(path(f'M{x-8} 142L{x+12} 168M{x-9} 165L{x+11} 145','none',sw=2) for x in (70,125,180,235,290,345,400))),
        'bamboo_stool':('Ghế tre',path('M126 158L333 137L372 182L165 212Z','#c2a573')+path('M142 180L135 293M345 173L356 284M171 211L178 302M335 197L333 298M139 253L174 271M179 270L334 257','none','#a88e61',10)),
        'rice_bundle':('Bó lúa', ''.join(path(f'M240 259Q{150+i*22} 155 {130+i*26} 87','none','#84915e',3)+ellipse(130+i*26,97,8,30,'#d7b65d',2) for i in range(9))+path('M209 219Q239 231 268 214M212 232Q240 246 263 228','none','#a86a48',6)),
        'lotus':('Hoa sen',path('M239 277L241 171','none','#7e9a6b',5)+ellipse(294,254,66,22,'#9aaf7a',2)+path('M240 192Q172 181 181 125Q222 129 240 159Q258 115 300 122Q310 176 240 192Z','#dba0a1')+path('M240 190Q207 156 241 105Q274 151 240 190Z','#eabbbc')),
        'tu_than_outfit':('Áo tứ thân và yếm',path('M183 66L129 86L103 177L143 195L166 143L144 290L225 288L240 218L256 289L337 290L314 143L337 194L377 177L351 86L296 66Z','#8e6348')+path('M212 69L240 162L269 69Z','#aa4b3c')+path('M177 191Q240 212 303 191M233 203L213 281M245 204L270 284','none',sw=5)),
        'brown_tunic':('Áo nâu',path('M180 66L127 86L101 179L140 196L163 147L154 287L325 287L316 147L338 196L378 179L350 86L298 66L263 65Q240 89 217 65Z','#88624a')+path('M216 67L239 96L265 67M239 96L240 281','none',sw=3)),
        'mo_qua_scarf':('Khăn mỏ quạ',path('M126 186Q92 60 240 58Q387 60 353 190L320 266L301 229L330 164Q283 134 240 86Q196 137 148 164L179 232L158 269Z','#302b2c')+path('M329 213L381 266L345 258L360 297L311 262Z','#302b2c')),
        'fish_trap':('Đó tre',path('M107 196Q181 80 358 132L392 203Q228 291 107 196Z','#c6ac79')+ellipse(373,168,26,38,'#74664b',3)+path('M124 188Q238 122 360 142M135 208Q242 159 365 158M169 228Q260 191 369 178M205 239Q285 212 373 192M186 135L224 249M245 120L279 234M306 123L330 215','none','#957e51',2)),
    }
    for key,(label,body) in props.items():
        save('props',key,label,body)


def house(x=220,y=210,s=1):
    b=path('M30 110H370V270H30Z','#f0e6cf')+path('M-4 109L46 26L350 26L409 109Q235 125-4 109Z','#c98866')
    b+=path('M34 26Q177 40 352 26M20 70Q195 88 384 70','none','#875f4c',2)
    b+=''.join(path(f'M{k} 35L{k-15} 105','none','#a66c54',2) for k in range(55,360,30))
    b+=path('M48 125V266M352 125V266M143 125V267M255 125V267','none','#795e49',7)
    b+=path('M163 144H237V266H163Z','#71604f')+path('M69 159H118V215H69ZM282 159H331V215H282Z','#d1c19d')
    b+=path('M20 274H380M10 286H390','none','#9b7a61',6)
    return f'<g transform="translate({x} {y}) scale({s})">{b}</g>'


def banyan(x=1050,y=130,s=1):
    b=path('M-20 122Q-31 234-68 290L-18 269L-2 294L24 271L74 292Q26 232 24 119Z','#a68b68')
    b+=path('M-5 162Q8 232-17 271M-42 145L-54 255M51 140L59 242','none','#7d7258',3)
    for cx,cy,rx in [(-110,71,75),(-57,18,83),(21,3,78),(95,45,85),(133,105,65),(55,108,87),(-55,118,89)]:
        b+=ellipse(cx,cy,rx,55,'#afbf8c',2.5)
    b+=path('M-95 142L-104 231M81 149L81 252M102 151L110 220','none','#93836a',2)
    return f'<g transform="translate({x} {y}) scale({s})">{b}</g>'


def build_backgrounds():
    for scene,label in [('courtyard','Sân nhà ba gian'),('pond','Ao làng cây đa'),('rice_fields','Đồng lúa'),('village_path','Đường làng'),('communal_house','Sân đình'),('market','Chợ quê'),('river','Bến sông'),('interior','Trong nhà')]:
        for time in ('day','night'):
            night=time=='night'
            sky,ground=('#e8eced','#e0e4dc') if night else ('#fffdf7','#f6f1e5')
            b=f'<path d="M0 0H1600V900H0Z" fill="{sky}" stroke="none"/>'
            b+=path('M0 530Q400 491 800 527T1600 519V900H0Z',ground,sw=2)
            b+=ellipse(1370,115,39,39,'#f6edcf' if night else '#ead29a',2)
            if night:
                b+=''.join(path(f'M{x} {y-5}V{y+5}M{x-5} {y}H{x+5}','none','#929fa3',2) for x,y in [(175,99),(660,155),(934,67),(1172,174),(1501,217)])
            if scene in ('courtyard','village_path','communal_house'):
                b+=house(190,225,.95 if scene!='communal_house' else 1.35)+banyan(1260,187,.95)
                b+=path('M87 625L1443 625M130 683H1403M200 748H1352','none','#d9bc9f',2)
                b+=''.join(path(f'M{x} 626L{x-40} 680M{x+30} 684L{x+5} 747','none','#d9bc9f',2) for x in range(250,1400,150))
                if scene=='village_path':
                    b+=path('M676 529Q638 635 384 900M809 529Q831 635 1212 900','none','#b9aa8c',3)
                if scene=='communal_house':
                    b+=path('M185 372Q148 369 133 330M742 372Q785 369 800 330','none','#87624b',6)
            elif scene=='pond':
                b+=house(120,254,.68)+banyan(1110,170,1)
                b+=ellipse(762,534,460,104,'#d7e4de',2)+path('M395 533H670M771 551H1020M552 584H818','none','#9dbab4',2)
                b+=ellipse(935,547,37,9,'#a4b48a',2)+path('M935 546V510M924 514Q935 492 947 514Z','#d8a0a4',sw=2)
            elif scene=='rice_fields':
                b+=path('M0 502L500 474L1600 491L1600 657L0 640Z','#ded7a8',sw=2)
                b+=path('M0 555L1600 541M0 602L1600 600M450 491L303 643M845 490L899 648M1200 492L1438 653','none','#a4ac77',3)
                for x in range(45,1570,75):
                    b+=path(f'M{x} 579l-7-14m7 14l9-19M{x+20} 627l-7-14m7 14l9-19','none','#a2a76d',2)
                b+=house(1180,330,.42)
            elif scene=='market':
                for x in (140,590,1040):
                    b+=path(f'M{x} 535V300H{x+340}V535','none','#9b805e',7)+path(f'M{x-25} 300L{x+30} 234H{x+310}L{x+365} 300Z','#c5ad85')+path(f'M{x+25} 477H{x+315}V530H{x+25}Z','#cdb48b')
                    for dx in (65,137,210):
                        b+=ellipse(x+dx,465,28,19,'#9fae7f',2)
            elif scene=='river':
                b+=path('M0 450Q592 426 1600 466V650Q702 610 0 667Z','#d7e4df',sw=2)
                b+=path('M170 511H410M691 485H1050M1100 562H1450M332 608H740','none','#a5bdb8',2)
                b+=path('M1032 572Q1172 619 1303 568L1269 618Q1164 648 1063 619Z','#a88764')+path('M1120 575L1183 491L1236 577Z','#ebddba')
                b+=path('M235 620L570 566M253 644L589 590M280 626L273 705M525 587L532 664','none','#aa956c',7)
                b+=banyan(1355,160,.75)
            else:
                b=path('M0 0H1600V900H0Z','#f6f0e3',sw=0)+path('M0 650H1600M170 0V650M1420 0V650','none','#9b8167',8)
                b+=path('M572 120H1028V650H572Z','#d0c6af')+path('M590 137H1010V650H590Z','#e4dfce')+path('M800 137V650','none','#a08e70',6)
                b+=path('M245 431H480V465H245ZM270 465V648M454 465V648','none','#957d5c',8)
                b+=path('M1160 266H1300V413H1160Z','#d2dcd1')+path('M1207 267V413M1254 267V413M1160 337H1300','none','#93856c',4)
            # Muted cool wash keeps night cartoons readable instead of turning the scene black.
            if night:
                b+='<path d="M0 0H1600V900H0Z" fill="#40516b" opacity=".12" stroke="none"/>'
            save('backgrounds',scene+'_'+time,label+(' · đêm' if night else ' · ngày'),b,'0 0 1600 900')


def build_effects():
    effects={
        'surprise':('Giật mình',path('M105 77L149 126M69 143L127 159M91 219L144 196M365 77L321 126M401 143L343 159M379 219L326 196','none',sw=7)),
        'sweat':('Giọt mồ hôi',path('M240 77Q170 171 192 222Q240 285 288 222Q310 171 240 77Z','#c5dfe4',sw=3)),
        'anger':('Tức giận',path('M184 111Q209 111 210 143M211 178Q210 207 183 211M244 143Q244 112 273 111M245 178Q244 209 273 211','none','#ae4b41',9)),
        'motion':('Vệt chuyển động',path('M81 123L377 108M119 183L340 175M74 242L378 237','none',sw=5)),
        'speech_bubble':('Bong bóng thoại',path('M107 74H369Q415 74 415 123V208Q415 251 365 251H199L137 297L149 251H108Q65 251 65 205V121Q65 74 107 74Z','#fff',sw=3)),
        'thought_bubble':('Bong bóng nghĩ',ellipse(242,151,160,97,'#fff',3)+ellipse(141,270,22,17,'#fff',3)+ellipse(107,309,10,9,'#fff',2)),
        'ghost_wisp':('Bóng ma truyện kể',path('M162 273Q192 240 177 168Q164 85 240 74Q315 85 303 168Q288 238 323 273L286 257L265 280L239 261L215 281L192 261Z','#e6eee9',sw=3)+face(241,146,True)),
        'dust':('Bụi chạy',ellipse(157,236,51,31,'#eee4d2',2)+ellipse(221,216,57,42,'#eee4d2',2)+ellipse(299,236,62,34,'#eee4d2',2)),
    }
    for key,(label,body) in effects.items():
        save('effects',key,label,body)


def main():
    build_characters()
    build_animals()
    build_props()
    build_backgrounds()
    build_effects()
    manifest={'style':'bac-bo-stick-10','version':1,'characters':list(PRESETS),'assets':CATALOG,
              'palette':{'ink':INK,'paper':'#fffdf7','earth':'#88624a','bib_red':'#b65a45','indigo':'#485f6a','foliage':'#afbf8c'},
              'notes':'Diễn giải hoạt hình Bắc Bộ theo mẫu 10 được duyệt; nguồn vector tách mảnh, không sao chép nhân vật kênh tham chiếu.'}
    (PACK/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
    print(f'{len(PRESETS)} rigs, {len(CATALOG)} scene/animal/prop/effect assets → {PACK}')


if __name__=='__main__':
    main()
