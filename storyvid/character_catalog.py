"""Public character choices and strict, non-mutating per-video resolution."""
import re

PRESETS = {
    'young_man': {'label': 'Nam trẻ · Tâm', 'female': False, 'age': 'young', 'scale': 1.0, 'skin': '#c89065', 'hair': '#292a28'},
    'young_woman': {'label': 'Nữ trẻ · Mai', 'female': True, 'age': 'young', 'scale': .96, 'skin': '#d3a17b', 'hair': '#252b29'},
    'elder_man': {'label': 'Ông · Ông Sáu', 'female': False, 'age': 'elder', 'scale': .94, 'skin': '#bc8d6e', 'hair': '#c6c4b8'},
    'elder_woman': {'label': 'Bà · Bà Tư', 'female': True, 'age': 'elder', 'scale': .90, 'skin': '#c49a7a', 'hair': '#bbbcb3'},
    'boy': {'label': 'Bé trai · Tí', 'female': False, 'age': 'child', 'scale': .76, 'skin': '#d3a075', 'hair': '#30302c'},
    'girl': {'label': 'Bé gái · Na', 'female': True, 'age': 'child', 'scale': .73, 'skin': '#d9aa83', 'hair': '#302e2b'},
    'middle_man': {'label': 'Nam trung niên · Chú Ba', 'female': False, 'age': 'middle', 'scale': 1.0, 'skin': '#b9845e', 'hair': '#343732'},
    'middle_woman': {'label': 'Nữ trung niên · Cô Hạnh', 'female': True, 'age': 'middle', 'scale': .96, 'skin': '#c69873', 'hair': '#34332d'},
}

def _extra_presets():
    """Characters an agent added under assets/bac-bo-stick/extra (see docs/pipeline.md)."""
    from .pack import manifest
    return {c['id']: {k: c[k] for k in ('label', 'female', 'age', 'scale', 'skin', 'hair')}
            for c in manifest()['extra_characters']}


PRESETS.update(_extra_presets())
OUTFITS = {'earth': {'label': 'Áo nâu đất', 'color': '#88624a'}, 'indigo': {'label':'Áo chàm', 'color':'#45616a'}, 'moss': {'label':'Áo xanh rêu', 'color':'#727453'}, 'cream': {'label':'Áo màu mộc', 'color':'#d0b994'}}
ACCESSORIES = {'none': 'Không phụ kiện', 'bag': 'Túi vải', 'scarf': 'Khăn rằn', 'flashlight': 'Đèn pin'}
COLORS = ('skin_color', 'hair_color', 'shirt_color', 'outline_color')


def validate_selection(value):
    if not isinstance(value, dict):
        raise ValueError('Cấu hình nhân vật phải là một object')
    clean = {}
    for key, choices in [('preset', PRESETS), ('outfit', OUTFITS), ('accessory', ACCESSORIES)]:
        if key in value:
            if not isinstance(value[key], str) or value[key] not in choices:
                raise ValueError(f'Lựa chọn nhân vật không hợp lệ: {key}')
            clean[key] = value[key]
    for key in COLORS:
        if key in value:
            if not isinstance(value[key], str) or not re.fullmatch(r'#[0-9a-fA-F]{6}', value[key]):
                raise ValueError(f'Màu không hợp lệ: {key}')
            clean[key] = value[key]
    return clean


def resolve_character(host, selection=None):
    """Preset palettes win when explicitly switching cast; explicit video colours win last."""
    selection = validate_selection(selection or {})
    defaults = validate_selection({k:v for k,v in host.items() if k in ('preset','outfit','accessory',*COLORS)})
    preset = selection.get('preset', defaults.get('preset', 'young_man'))
    outfit = selection.get('outfit', defaults.get('outfit', 'earth'))
    info = PRESETS[preset]
    result = {'preset': preset, 'outfit': outfit, 'accessory': selection.get('accessory', defaults.get('accessory', 'none')),
              'skin_color': info['skin'], 'hair_color': info['hair'], 'shirt_color': OUTFITS[outfit]['color'], 'outline_color': '#34332e'}
    if preset == defaults.get('preset', 'young_man'):
        result.update({k:v for k,v in defaults.items() if k in COLORS})
    if 'outfit' in selection:
        result['shirt_color'] = OUTFITS[outfit]['color']
    result.update({k:v for k,v in selection.items() if k in COLORS})
    return result
