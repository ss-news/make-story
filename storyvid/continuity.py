"""Human-approved visual references, independent of scenes/visuals contracts.

refs/continuity.json stores places/props and the approval snapshot. Reference content,
not file size, is hashed. Generation receipts track which outputs still match their inputs.
"""
import hashlib
import json
import threading
from functools import lru_cache
from pathlib import Path

from . import places

_lock = threading.RLock()


def read(path: Path, default=None):
    return json.loads(path.read_text(encoding='utf-8')) if path.is_file() else default


def load(project: Path) -> dict:
    return read(project / 'refs/continuity.json', {'assets': []})


def save(project: Path, data: dict) -> None:
    with _lock:
        path = project / 'refs/continuity.json'
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix('.tmp')
        tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        tmp.replace(path)


def file(project: Path, name: str) -> Path | None:
    if not isinstance(name, str) or not name:
        return None
    target = (project / name).resolve()
    return target if target.is_relative_to(project.resolve()) and target.is_file() else None


@lru_cache(maxsize=4096)
def _content(path: str, stamp: tuple) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def content(project: Path, name: str) -> str:
    target = file(project, name)
    if not target:
        return 'missing'
    st = target.stat()
    return _content(str(target), (st.st_mtime_ns, st.st_ctime_ns, st.st_size, st.st_ino))


def hashed(value) -> str:
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True).encode()).hexdigest()


def references(project: Path, i: int) -> tuple[str, list[Path]]:
    notes, refs = [], []
    for a in load(project).get('assets', []):
        if i + 1 in a.get('scenes', []):
            target = file(project, a.get('image', ''))
            if target:
                refs.append(target)
                notes.append(f"Locked {a['kind']} — {a['name']}: {a['description']}. "
                             "Match the attached reference's design, geometry, materials and colours. "
                             "Only the camera, action and story-specified state may change.")
    return '\n'.join(notes), refs


def snapshot(project: Path, only: int | None = None):
    script = read(project / 'scenes.json', {})
    v = read(project / 'visuals.json', {}) or {}
    assets = load(project).get('assets', [])
    cast = v.get('cast', [])
    scenes = v.get('scenes', [])
    if only is not None:
        assets = [a for a in assets if only + 1 in a.get('scenes', [])]
        actors = {a['id'] for a in script['scenes'][only].get('actors', [])}
        cast = [c for c in cast if c['id'] in actors]
        scenes = scenes[only:only + 1]
        script = script['scenes'][only]
    return {
        'script': script, 'style': v.get('style'), 'ratio': v.get('ratio'),
        'continuity': v.get('continuity', 'auto'),
        'storyboard': read(project / 'storyboard.json'),
        'cast': [(c['id'], c['look'], c['sheet'], content(project, c['sheet'])) for c in cast],
        'style_refs': [(p, content(project, p)) for p in v.get('style_refs', [])],
        'assets': [(a, content(project, a.get('image', ''))) for a in assets],
        'places': [(p, [(f, content(project, f)) for f in p.get('files', [])])
                   for p in places.load(project)['places']],
        'prompts': [{k: s.get(k) for k in ('image_prompt', 'video_prompt', 'negative')} for s in scenes],
    }


def digest(project: Path) -> str:
    return hashed(snapshot(project))


def scene_digest(project: Path, i: int) -> str:
    return hashed(snapshot(project, i))


def scene_links(project: Path) -> list[bool]:
    from .visuals import linked
    from .storyboard import load as load_board, aligned
    script = read(project / 'scenes.json')
    return linked(script, read(project / 'visuals.json'), aligned(load_board(project), script))


def input_digest(project: Path, i: int, kind: str) -> str:
    value = {'scene': scene_digest(project, i)}
    if kind == 'clip':
        scenes = read(project / 'visuals.json')['scenes']
        value['opening'] = content(project, scenes[i].get('image', ''))
        if scene_links(project)[i]:
            value['previous'] = content(project, scenes[i - 1].get('clip', ''))
    return hashed(value)


def record(project: Path, i: int, kind: str, inputs: str | None = None) -> None:
    with _lock:
        path = project / 'refs/generated.json'
        data = read(path, {})
        v = read(project / 'visuals.json')
        data.setdefault(str(i), {})[kind] = {'inputs': inputs or input_digest(project, i, kind),
                                           'output': content(project, v['scenes'][i][kind])}
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix('.tmp')
        tmp.write_text(json.dumps(data, indent=2) + '\n')
        tmp.replace(path)


def current(project: Path, i: int, kind: str, memo: dict | None = None) -> bool:
    memo = {} if memo is None else memo
    key = (i, kind)
    if key in memo:
        return memo[key]
    receipt = read(project / 'refs/generated.json', {}).get(str(i), {}).get(kind, {})
    memo[key] = False
    if not receipt:
        return False
    v = read(project / 'visuals.json', {}) or {}
    if i >= len(v.get('scenes', [])):
        return False
    scene = v['scenes'][i]
    if kind == 'clip':
        if not current(project, i, 'image', memo):
            return False
        # Every preceding continuous shot must still match its own references.
        if scene_links(project)[i] and not current(project, i - 1, 'clip', memo):
            return False
    memo[key] = bool(file(project, scene.get(kind, '')) and receipt.get('inputs') == input_digest(project, i, kind)
                     and receipt.get('output') == content(project, scene[kind]))
    return memo[key]


def errors(project: Path) -> list[str]:
    from .visuals import linked
    from .storyboard import load as load_board, aligned
    script = read(project / 'scenes.json', {})
    v = read(project / 'visuals.json', {}) or {}
    out, ids = [], set()
    n = len(script.get('scenes', []))
    if not n or len(v.get('scenes', [])) != n:
        return ['Cần kịch bản và đủ prompt hình trước khi duyệt bộ mẫu.']
    for a in load(project).get('assets', []):
        name = a.get('name') or a.get('id') or '?'
        if not a.get('id') or a['id'] in ids:
            out.append(f'{name}: mã mẫu trống hoặc trùng.')
        ids.add(a.get('id'))
        if a.get('kind') not in ('place', 'prop') or not str(a.get('description', '')).strip():
            out.append(f'{name}: chọn loại và mô tả đặc điểm cố định.')
        if not file(project, a.get('image', '')):
            out.append(f'{name}: thiếu ảnh tham chiếu trong dự án.')
        nums = a.get('scenes', [])
        if not nums or any(type(x) is not int or x < 1 or x > n for x in nums):
            out.append(f'{name}: gán số cảnh từ 1 đến {n}.')
    for p in places.load(project)['places']:
        if not p.get('files') or not file(project, p['files'][0]):
            out.append(f"{p.get('name', p['id'])}: thiếu ảnh địa điểm.")
    links = linked(script, v, aligned(load_board(project), script))
    for i, s in enumerate(script['scenes']):
        extra = references(project, i)[1]
        legacy = [f for _, files in places.for_scene(project, script, v, i) for f in files]
        actor_count = len({a['id'] for a in s.get('actors', []) if any(c['id'] == a['id'] for c in v.get('cast', []))})
        styling = len(v.get('style_refs', []))
        if actor_count + len(extra) + len(legacy) + styling > 4 or (2 if links[i] else 1) + actor_count + len(extra) + len(legacy) > 4:
            out.append(f'Cảnh {i + 1}: vượt 4 ảnh tham chiếu; giảm số chủ thể hoặc ghép bảng mẫu cùng loại.')
    return out


def status(project: Path) -> dict:
    problems = errors(project)
    v = read(project / 'visuals.json', {}) or {}
    memo = {}
    stale = [i + 1 for i, s in enumerate(v.get('scenes', []))
             if any(s.get(k) and not current(project, i, k, memo) for k in ('image', 'clip'))]
    data = load(project)
    return {'assets': data.get('assets', []), 'approved': not problems and data.get('approved') == digest(project),
            'errors': problems, 'stale': stale}


def require(project: Path) -> None:
    problems = errors(project)
    if problems or load(project).get('approved') != digest(project):
        raise RuntimeError('Duyệt bộ mẫu ở mục Khóa hình ảnh trước khi tạo cảnh. ' + ' '.join(problems[:3]))
