"""Editable SVG parts composed around named joints, rasterized once per animation state."""
import io
import json
from pathlib import Path
from xml.etree import ElementTree as ET

import resvg_py
from PIL import Image

from .character_catalog import PRESETS, resolve_character

UNIT_W, UNIT_H = 480, 640
ASSETS = Path(__file__).resolve().parents[1] / 'assets' / 'bac-bo-stick' / 'characters'
# Rotation from vertically down, in degrees, at shoulder and elbow.
ARM_POSES = {
    'idle': ((8, -5), (-8, 5)),
    'talk': ((8, -5), (-65, -55)),
    'point': ((8, -5), (-85, -5)),
    'scared': ((95, 55), (-95, -55)),
    'think': ((8, -5), (-38, -112)),
    'shrug': ((55, 75), (-55, -75)),
    'reach': ((8, -5), (-80, -15)),
    'wave': ((8, -5), (-150, -30)),
    'cower': ((-25, -105), (25, 105)),
}
# Front-view walk: how far each leg is lifted per frame (units); the right leg runs half a cycle behind.
WALK_CYCLE = [16, 6, 0, 6]



class Character:
    def __init__(self, host, height_px, *, asset_root=None):
        self.config = resolve_character(host)
        self.preset = self.config['preset']
        self.folder = (Path(asset_root) if asset_root is not None else ASSETS) / self.preset
        self.rig = json.loads((self.folder / 'rig.json').read_text())
        self.height = height_px
        self.width = round(height_px * UNIT_W / UNIT_H)
        self.parts = {name: self._load_part(info) for name,info in self.rig['parts'].items()}
        self._sprites = {}

    def _load_part(self, info):
        root = ET.fromstring((self.folder / info['file']).read_text())
        body = ''.join(ET.tostring(child, encoding='unicode') for child in root)
        colors = {'skin':self.config['skin_color'], 'hair':self.config['hair_color'], 'shirt':self.config['shirt_color'],
                  'ink':self.config['outline_color'], 'pants':'#454c47'}
        for token,color in colors.items():
            body = body.replace('{{'+token+'}}', color)
        return body

    def _part(self, name, x=0, y=0, angle=0, mirror=False):
        px,py = self.rig['parts'][name]['pivot']
        return f'<g transform="translate({x} {y}) rotate({angle}) scale({-1 if mirror else 1} 1) translate({-px} {-py})">{self.parts[name]}</g>'

    def _face(self, expression, mouth, blink):
        if expression not in ('neutral','happy','scared','surprised','sad','angry','smirk'):
            expression = 'neutral'
        mouth_state = 'open' if mouth == 2 else 'half' if mouth == 1 else expression
        return (self._part('brows_'+expression) + self._part('eyes_'+('closed' if blink else expression))
                + self._part('mouth_'+mouth_state))

    def _arm(self, side, angles):
        x,y = self.rig['anchors']['shoulder_'+side]
        upper, lower = angles
        length = self.rig['lengths']
        out = f'<g transform="translate({x} {y}) rotate({upper})">'+self._part('upper_arm')
        out += f'<g transform="translate(0 {length["upper_arm"]}) rotate({lower})">'+self._part('forearm')
        out += self._part('hand',0,length['forearm'],mirror=side=='R')
        if side=='R' and self.config['accessory']=='flashlight':
            out += self._part('flashlight',0,length['forearm']+9,angle=90)
        return out+'</g></g>'

    def svg(self, pose='idle', expression='neutral', mouth=0, blink=False, flip=False, step=None):
        """Return the assembled editable SVG; each source part stays in its own group."""
        anchors = self.rig['anchors']
        length = self.rig['lengths']
        layers = []
        # Legs have independent pivots; `step` picks a walk-cycle frame, None keeps feet planted.
        for side in ('L','R'):
            x,y = anchors['hip_'+side]
            lift = 0 if step is None else WALK_CYCLE[(step + (0 if side == 'L' else 2)) % len(WALK_CYCLE)]
            splay = (lift / 4) * (1 if side == 'L' else -1)  # lifted foot swings slightly outward
            layers.append(f'<g transform="translate({x} {y - lift}) rotate({splay})">' + self._part('thigh')
                          + f'<g transform="translate(0 {length["thigh"]})">' + self._part('shin')
                          + self._part('foot', 0, length['shin'], mirror=side=='R') + '</g></g>')
        hx,hy = anchors['head']
        head_scale = self.rig.get('head_scale', 1)
        def head_layer(body):
            return f'<g transform="translate({hx} {hy}) scale({head_scale})">{body}</g>'
        layers.append(head_layer(self._part('hair_back')))
        layers.append(self._part('neck',*anchors['neck']))
        layers.append(self._part('torso',*anchors['torso']))
        accessory = self.config['accessory']
        if accessory in ('bag','scarf'):
            layers.append(self._part(accessory,*anchors['torso']))
        a,b = ARM_POSES.get(pose, ARM_POSES['idle'])
        layers += [self._arm('L',a),self._arm('R',b)]
        # Head above hands avoids a forearm obscuring the mouth in the thinking pose.
        layers.append(head_layer(self._part('head')))
        layers.append(head_layer(self._face(expression,mouth,blink)))
        layers.append(head_layer(self._part('hair_front')))
        scale = self.rig['scale']
        # Common ground line at y=608; smaller cast remains shorter in the same video canvas.
        transform = f'translate({200*(1-scale)} {608*(1-scale)}) scale({scale})'
        body = f'<g transform="{transform}">'+''.join(layers)+'</g>'
        if flip:
            body = '<g transform="translate(400 0) scale(-1 1)">'+body+'</g>'
        return f'<svg xmlns="http://www.w3.org/2000/svg" width="{self.width}" height="{self.height}" viewBox="-40 0 480 640">{body}</svg>'

    def head(self, flip=False):
        """(x, y, radius) of the head in sprite pixels, for placing effects around it."""
        hx,hy = self.rig['anchors']['head']
        scale = self.rig['scale']
        x, y = 200*(1-scale) + hx*scale, 608*(1-scale) + hy*scale
        if flip:
            x = 400 - x
        radius = 90 * self.rig.get('head_scale', 1) * scale
        return (x+40) * self.width/480, y * self.height/640, radius * self.height/640

    def sprite(self, pose, expression, mouth, blink, flip, step=None):
        key = (pose,expression,mouth,blink,flip,step)
        if key not in self._sprites:
            data = resvg_py.svg_to_bytes(svg_string=self.svg(*key), width=self.width*2, height=self.height*2)
            self._sprites[key] = Image.open(io.BytesIO(data)).convert('RGBA').resize((self.width,self.height),Image.Resampling.LANCZOS)
        return self._sprites[key]
