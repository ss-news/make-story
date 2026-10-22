"""Build the initial editable vector library. Run explicitly: overwrites generated SVGs."""
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from storyvid.character_catalog import PRESETS
ROOT = Path(__file__).resolve().parents[1] / 'assets' / 'characters'

def svg(body):
    return '<svg xmlns="http://www.w3.org/2000/svg" viewBox="-120 -130 240 300"><g stroke="{{ink}}" stroke-width="3.2" stroke-linejoin="round" stroke-linecap="round">' + body + '</g></svg>\n'

for name, info in PRESETS.items():
    female, age = info['female'], info['age']
    folder = ROOT / name
    folder.mkdir(parents=True, exist_ok=True)
    parts = {
        'neck': '<path d="M-17-12H17L19 31Q0 43-19 31Z" fill="{{skin}}"/><path d="M-15 0Q0 13 15 0" fill="none" opacity=".18"/>',
        'torso': '<path d="M-30-4Q-54-3-64 18L-51 77-49 160Q0 173 49 160L51 77 64 18Q54-3 30-4L15 8H-15Z" fill="{{shirt}}"/><path d="M-15 4 0 26 15 4M0 27V158" fill="none" opacity=".5"/><path d="M-39 87H-14V113H-39ZM17 87H42V113H17Z" fill="{{shirt}}" stroke-opacity=".4"/><path d="M-44 139Q-25 143-11 139M11 139Q31 144 44 139" fill="none" opacity=".23"/><g fill="{{ink}}" stroke="none"><circle cy="49" r="2"/><circle cy="73" r="2"/><circle cy="121" r="2"/></g>',
        'upper_arm': '<path d="M-19 0Q-24 12-20 30L-17 68Q0 78 17 68L20 30Q24 12 19 0Z" fill="{{shirt}}"/><path d="M-16 61Q0 68 16 61" fill="none" opacity=".35"/>',
        'forearm': '<path d="M-14-3Q-18 24-12 69Q0 78 12 69L14-3Z" fill="{{skin}}"/><path d="M-9 12-5 54" fill="none" stroke="#ffffff" opacity=".12"/>',
        'hand': '<path d="M-10-5Q-17 1-13 17L-9 29Q-3 34 2 28 10 30 12 21L11 6Q20 17 22 8L12-5Z" fill="{{skin}}"/><path d="M-7 14-5 25M0 14 1 26M7 13 7 23" fill="none" stroke-width="1.4" opacity=".45"/>',
        'thigh': '<path d="M-23-7H23L21 78Q0 86-21 78Z" fill="{{pants}}"/><path d="M12 7 11 65" fill="none" opacity=".23"/>',
        'shin': '<path d="M-20-5H20L16 55H-16Z" fill="{{pants}}"/><path d="M-17 47H17V59H-17Z" fill="{{pants}}"/><path d="M-12 59H12L13 78H-13Z" fill="{{skin}}"/>',
        'foot': '<path d="M-13-3Q-23-3-27 8L-28 16H17L15 1Z" fill="{{skin}}"/><path d="M-29 14H18V21H-29Z" fill="#595749"/><path d="M-17 2-4 14 7 1" fill="none" stroke="#888875" stroke-width="6"/>',
        'hair_back': '',
    }
    # Soft asymmetric faces, ears, nose shading; expressions are separate live layers.
    jaw = 59 if female else 65
    parts['head'] = f'<ellipse cx="-66" cy="5" rx="11" ry="17" fill="{{{{skin}}}}"/><ellipse cx="66" cy="5" rx="11" ry="17" fill="{{{{skin}}}}"/><path d="M-64-35Q-60-82 0-82 63-80 66-34L62 22Q{jaw} 65 0 78Q-{jaw} 65-62 22Z" fill="{{{{skin}}}}"/><path d="M-59 20Q-49 57 0 70 43 63 58 25" fill="none" stroke="#986447" opacity=".22" stroke-width="6"/><path d="M-3 7-7 27 3 29" fill="none" stroke="#956448" stroke-width="2.5"/><ellipse cx="-36" cy="35" rx="13" ry="5" fill="#bd715b" opacity=".23"/><ellipse cx="36" cy="35" rx="13" ry="5" fill="#bd715b" opacity=".23"/>'
    if age == 'elder':
        parts['head'] += '<g fill="none" stroke-width="1.5" opacity=".48"><path d="M-33-29Q0-38 33-29M-27-23Q0-30 27-23M-48 20-57 24M48 20 57 24M-30 37-35 53M30 37 35 53M-18 65Q0 70 18 65"/></g>'
    elif age == 'middle':
        parts['head'] += '<path d="M-48 22-55 25M48 22 55 25M-25 41-30 53M25 41 30 53" fill="none" stroke-width="1.5" opacity=".35"/>'
    if female:
        if age == 'child':
            parts['hair_back'] = '<path d="M-53-27Q-103-19-88 37L-68 16Q-76 1-53 4M53-27Q103-19 88 37L68 16Q76 1 53 4" fill="{{hair}}"/><path d="M-80-4-65-5M65-5 80-4" stroke="{{shirt}}" stroke-width="8"/>'
        else:
            parts['hair_back'] = '<path d="M-68-40Q-81 11-62 86L-42 103H42L62 86Q81 11 68-40Z" fill="{{hair}}"/>' if age == 'young' else '<ellipse cy="-77" rx="36" ry="24" fill="{{hair}}"/>'
        parts['hair_front'] = '<path d="M-65 11Q-85-49-46-76 0-107 46-76 84-50 66 11L53-24Q20-30 3-67-6-35-56-20Z" fill="{{hair}}"/><path d="M-49-55Q-29-79-7-79M21-71Q50-56 55-37" fill="none" stroke="#ffffff" stroke-width="3" opacity=".13"/>'
    elif age == 'elder':
        parts['hair_front'] = '<path d="M-65 5Q-81-39-54-65L-32-61Q-60-32-53 7ZM65 5Q81-39 54-65L32-61Q60-32 53 7Z" fill="{{hair}}"/><path d="M-31-73Q0-91 28-73" fill="none" stroke="{{hair}}" stroke-width="10"/>'
    else:
        parts['hair_front'] = '<path d="M-65 10Q-83-29-62-64L-43-70-32-85-12-80 9-91 26-79Q71-82 74-35L64 8 52-27Q29-26 12-50-4-28-35-29L-54-17Z" fill="{{hair}}"/><path d="M-47-55Q-21-68 1-66M22-66Q44-60 54-44" fill="none" stroke="#ffffff" stroke-width="3" opacity=".12"/>'
    if age == 'middle' and not female:
        parts['hair_front'] += '<path d="M-61-13-55-4M61-13 55-4" stroke="#919487" stroke-width="6"/>'
        parts['head'] += '<path d="M-17 43Q-6 35 0 42 6 35 17 43L12 47H-12Z" fill="{{hair}}" stroke="none"/>'
    if female:
        parts['torso'] = parts['torso'].replace('L-51 77-49 160', 'L-43 77-52 160').replace('49 160L51 77','52 160L43 77')
    if age == 'child':
        parts['torso'] = '<path d="M-27-4Q-54-3-64 18L-51 65-47 158Q0 168 47 158L51 65 64 18Q54-3 27-4L15 8H-15Z" fill="{{shirt}}"/><path d="M-15 4Q0 24 15 4M-42 143Q0 149 42 143" fill="none" opacity=".45"/><path d="M17 57H39V80H17Z" fill="none" opacity=".5"/>'
    parts['bag'] = '<path d="M-47 0 48 124" fill="none" stroke="#a4916c" stroke-width="9"/><path d="M21 102Q40 94 65 105L61 157Q43 165 23 155Z" fill="#b6a17d"/><path d="M26 107 58 112 55 129 28 126Z" fill="#9d8967"/>'
    parts['scarf'] = '<path d="M-25-5Q0 18 25-5L32 10 14 26 24 88 3 94-4 29-28 13Z" fill="#d1c5a7"/><path d="M10 32 19 88M5 35 13 91M-26 6 27 6M-19 13 20 13M5 43 17 42M7 55 19 54M8 67 21 66M9 79 22 78" fill="none" stroke="#676b61" stroke-width="2"/>'
    parts['flashlight'] = '<path d="M-8-12H8V22H-8Z" fill="#646e64"/><path d="M-12-22H12V-10H-12Z" fill="#9a9d89"/><path d="M-9-24H9" stroke="#dfd2a1" stroke-width="5"/><circle cy="2" r="3" fill="#d5c185"/>'
    metadata = {}
    for part, body in parts.items():
        (folder / f'{part}.svg').write_text(svg(body))
        metadata[part] = {'file': f'{part}.svg', 'pivot': [0,0]}
    rig = {'viewBox': [0,0,400,640], 'scale': info['scale'], 'parts': metadata,
           'anchors': {'head':[200,170], 'neck':[200,244], 'torso':[200,270], 'shoulder_L':[144,287], 'shoulder_R':[256,287], 'hip_L':[174,427], 'hip_R':[226,427]},
           'lengths': {'upper_arm':68,'forearm':69,'thigh':78,'shin':78}, 'face': {'eye_y':10,'mouth_y':51}}
    (folder / 'rig.json').write_text(json.dumps(rig, indent=2)+'\n')
print(f'Built {len(PRESETS)} editable character rigs in {ROOT}')

# Facial components are editable source files too, selected independently by animation.
for name, info in PRESETS.items():
    folder = ROOT / name
    rig = json.loads((folder/'rig.json').read_text())
    face_parts = {}
    for expression in ('neutral','happy','scared','surprised','sad','angry','smirk','closed'):
        brows,eyes = [],[]
        slopes = {'angry':(0,8),'sad':(5,-2),'scared':(-9,-13),'surprised':(-9,-12)}.get(expression,(0,0))
        for side in (-1,1):
            x,y=side*27,10
            brows.append(f'<path d="M{x-12} {y-18+slopes[0 if side<0 else 1]} Q{x} {y-22} {x+12} {y-18+slopes[1 if side<0 else 0]}" fill="none" stroke="{{{{ink}}}}" stroke-width="4"/>')
            if expression=='closed' or (expression=='smirk' and side==1):
                eyes.append(f'<path d="M{x-9} {y}Q{x} {y+3} {x+9} {y}" fill="none"/>')
            elif expression=='happy':
                eyes.append(f'<path d="M{x-9} {y+2}Q{x} {y-10} {x+9} {y+2}" fill="none"/>')
            else:
                ry=12 if expression in ('scared','surprised') else 7
                eyes.append(f'<ellipse cx="{x}" cy="{y}" rx="10" ry="{ry}" fill="#f6edda" stroke-width="1.8"/><ellipse cx="{x+1}" cy="{y+1}" rx="4" ry="6" fill="{{{{ink}}}}" stroke="none"/><circle cx="{x+2}" cy="{y-2}" r="1.5" fill="#fff" stroke="none"/>')
                if info['female']:
                    eyes.append(f'<path d="M{x-9} {y-3}l-3-3" fill="none" stroke-width="1.8"/>')
        face_parts['brows_'+expression]=''.join(brows)
        face_parts['eyes_'+expression]=''.join(eyes)
    for expression in ('neutral','happy','scared','surprised','sad','angry','smirk','half','open'):
        if expression in ('half','open'):
            body=f'<ellipse cy="51" rx="{10 if expression=="half" else 13}" ry="{5 if expression=="half" else 11}" fill="#6d3e32"/><path d="M-6 56Q0 52 6 56" stroke="#c68673" fill="none"/>'
        elif expression in ('happy','smirk'):
            body='<path d="M-14 48Q0 63 16 47" fill="none"/>'
        elif expression=='sad':
            body='<path d="M-12 54Q0 45 12 54" fill="none"/>'
        elif expression in ('scared','surprised'):
            body='<ellipse cy="51" rx="6" ry="8" fill="#6d3e32"/>'
        else:
            body='<path d="M-11 51Q0 54 11 51" fill="none"/>'
        face_parts['mouth_'+expression]=body
    for part,body in face_parts.items():
        (folder/f'{part}.svg').write_text(svg(body))
        rig['parts'][part]={'file':f'{part}.svg','pivot':[0,0]}
    rig['head_scale']=1.17 if info['age']=='child' else 1.0
    (folder/'rig.json').write_text(json.dumps(rig,indent=2)+'\n')
