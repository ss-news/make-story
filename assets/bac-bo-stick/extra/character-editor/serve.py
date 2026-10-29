"""Local character-layout editor. No third-party packages required."""
import argparse
import json
import math
import mimetypes
import os
import re
import tempfile
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit, unquote

HERE = Path(__file__).resolve().parent
PACK = HERE.parent / 'human-action-trial-v1'
ROOT = HERE.parents[3]
SAVES = ROOT / 'output/stung_treng/character-editor/layouts'
ASSETS = {p['id']: PACK / p['file'] for p in json.loads((PACK/'manifest.json').read_text())['parts']}
MAX_BODY = 100_000

def safe_name(value):
    if not isinstance(value,str) or not re.fullmatch(r'[a-zA-Z0-9_-]{1,80}',value):
        raise ValueError('Tên bản lưu chỉ gồm chữ không dấu, số, dấu - hoặc _.')
    return value

def number(value, lo, hi):
    if isinstance(value,bool) or not isinstance(value,(float,int)) or not math.isfinite(value) or not lo <= value <= hi:
        raise ValueError('Thông số ngoài giới hạn hoặc không phải số hữu hạn.')

def validate_document(doc):
    if not isinstance(doc,dict) or doc.get('format')!='character-layout/1' or doc.get('source')!='human-action-trial-v1':
        raise ValueError('Cấu hình không đúng định dạng hoặc bộ nhân vật.')
    canvas=doc.get('canvas')
    if not isinstance(canvas,dict):raise ValueError('Thiếu kích thước khung.')
    for key in ('width','height'):number(canvas.get(key),100,4096)
    parts=doc.get('parts')
    if not isinstance(parts,list) or not 1<=len(parts)<=40:raise ValueError('Cần từ 1 đến 40 bộ phận.')
    ids=set()
    for p in parts:
        if not isinstance(p,dict):raise ValueError('Bộ phận không hợp lệ.')
        safe_name(p.get('id'))
        if p['id'] in ids:raise ValueError('Trùng mã bộ phận.')
        ids.add(p['id'])
        if p.get('asset') not in ASSETS:raise ValueError('Ảnh không nằm trong bộ nhân vật.')
        for key in ('x','y'):number(p.get(key),-8192,8192)
        for key in ('width','height'):number(p.get(key),1,4096)
        for key in ('pivotX','pivotY'):number(p.get(key),0,1)
        number(p.get('rotation'),-360,360);number(p.get('z'),-100,100)
        if not isinstance(p.get('visible'),bool):raise ValueError('Trạng thái hiển thị không hợp lệ.')
    if 'title' in doc and (not isinstance(doc['title'],str) or len(doc['title'])>160):raise ValueError('Tên quá dài.')
    return doc

class Handler(BaseHTTPRequestHandler):
    def reply(self,code,value):
        data=json.dumps(value,ensure_ascii=False,allow_nan=False).encode()
        self.send_response(code);self.send_header('Content-Type','application/json; charset=utf-8')
        self.send_header('Content-Length',str(len(data)));self.send_header('Cache-Control','no-store');self.end_headers();self.wfile.write(data)
    def host_ok(self):
        return self.headers.get('Host') in {f'127.0.0.1:{self.server.server_port}',f'localhost:{self.server.server_port}'}
    def do_GET(self):
        if not self.host_ok():return self.reply(403,{'error':'Chỉ nhận kết nối localhost.'})
        path=unquote(urlsplit(self.path).path)
        try:
            if path=='/api/configs':
                SAVES.mkdir(parents=True,exist_ok=True)
                return self.reply(200,{'names':sorted(p.stem for p in SAVES.glob('*.json'))})
            if path.startswith('/api/configs/'):
                name=safe_name(path.removeprefix('/api/configs/'))
                return self.reply(200,json.loads((SAVES/f'{name}.json').read_text()))
            if path.startswith('/source/'):
                key=path.removeprefix('/source/')
                file=PACK/'background.png' if key=='background' else ASSETS.get(key)
            else:
                file=HERE/({'/':'index.html'}.get(path,path.lstrip('/')))
                if file.parent != HERE or file.name not in {'index.html','style.css','model.js','app.js'}:file=None
            if file is None or not file.is_file():return self.reply(404,{'error':'Không tìm thấy.'})
            data=file.read_bytes();self.send_response(200)
            self.send_header('Content-Type',mimetypes.guess_type(file)[0] or 'application/octet-stream')
            self.send_header('Content-Length',str(len(data)));self.send_header('Cache-Control','no-cache');self.end_headers();self.wfile.write(data)
        except FileNotFoundError:self.reply(404,{'error':'Bản lưu không còn tồn tại.'})
        except ValueError as e:self.reply(400,{'error':str(e)})
    def do_POST(self):
        if not self.host_ok():return self.reply(403,{'error':'Host không hợp lệ.'})
        if self.headers.get('Origin') != f"http://{self.headers.get('Host')}":return self.reply(403,{'error':'Nguồn ghi không hợp lệ.'})
        if self.headers.get('Content-Type','').split(';')[0]!='application/json':return self.reply(415,{'error':'Cần JSON.'})
        try:
            path=unquote(urlsplit(self.path).path)
            if not path.startswith('/api/configs/'):return self.reply(404,{'error':'Không tìm thấy.'})
            name=safe_name(path.removeprefix('/api/configs/'));size=int(self.headers.get('Content-Length','0'))
            if not 0<size<=MAX_BODY:return self.reply(413,{'error':'Cấu hình quá lớn hoặc rỗng.'})
            doc=validate_document(json.loads(self.rfile.read(size)))
            SAVES.mkdir(parents=True,exist_ok=True)
            fd,temp=tempfile.mkstemp(dir=SAVES,suffix='.tmp')
            try:
                with os.fdopen(fd,'w') as out:json.dump(doc,out,ensure_ascii=False,allow_nan=False,indent=2)
                os.replace(temp,SAVES/f'{name}.json')
            finally:
                if os.path.exists(temp):os.unlink(temp)
            self.reply(200,{'saved':name,'path':str(SAVES/f'{name}.json')})
        except (ValueError,TypeError) as e:self.reply(400,{'error':str(e)})
        except OSError:self.reply(500,{'error':'Không ghi được cấu hình. Hãy xuất JSON để giữ bản chỉnh.'})

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--port',type=int,default=8766);ap.add_argument('--open',action='store_true');args=ap.parse_args()
    print(f'Character editor: http://127.0.0.1:{args.port}',flush=True)
    server=ThreadingHTTPServer(('127.0.0.1',args.port),Handler)
    if args.open:
        import webbrowser
        webbrowser.open(f'http://127.0.0.1:{args.port}')
    server.serve_forever()
