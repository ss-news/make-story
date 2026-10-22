"""Render the eight casts through all poses, without network/TTS or touching existing videos."""
import json
import subprocess
import sys
import wave
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import numpy as np
from storyvid.backgrounds import _procedural
from storyvid.character_catalog import PRESETS
from storyvid.ffmpeg import ffmpeg_exe
from storyvid.render import Renderer
from storyvid.script import POSES, EXPRESSIONS
from storyvid.tts import SAMPLE_RATE
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'output'/'character-library'/'demos'
OUT.mkdir(parents=True,exist_ok=True)
channel=json.loads((ROOT/'channel.json').read_text())
bg=OUT/'village.png'
_procedural('bamboo village at dusk','character-demo',(982,552)).save(bg)
fps=15; span=.8; duration=len(POSES)*span
# Low-level synthetic audio exercises lip flap; this is a motion test, not a narrated story.
t=np.arange(round(duration*SAMPLE_RATE))/SAMPLE_RATE
samples=(np.sin(2*np.pi*180*t)*np.maximum(0,np.sin(2*np.pi*3*t))*6000).astype(np.int16)
audio=OUT/'motion-test.wav'
with wave.open(str(audio),'wb') as w:
    w.setnchannels(1);w.setsampwidth(2);w.setframerate(SAMPLE_RATE);w.writeframes(samples.tobytes())
clips=[]
for i,(preset,info) in enumerate(PRESETS.items()):
    folder=OUT/preset;folder.mkdir(exist_ok=True)
    scenes=[{'narration':info['label'],'bg_id':'village','bg_prompt':'bamboo village at dusk','pose':p,'expression':EXPRESSIONS[j], 'position':'center','camera':'static'} for j,p in enumerate(POSES)]
    choice={'preset':preset,'outfit':['earth','indigo','moss','cream'][i%4],'accessory':['none','bag','scarf','flashlight'][i%4]}
    script={'title':info['label'],'character':choice,'scenes':scenes}
    (folder/'scenes.json').write_text(json.dumps(script,ensure_ascii=False,indent=2)+'\n')
    timeline={'audio':audio,'samples':samples,'duration':duration,'scenes':[{'start':j*span,'end':(j+1)*span} for j in range(len(scenes))], 'cues':[{'start':0,'end':duration,'text':info['label']}]}
    video=folder/'video.mp4'
    Renderer(channel,(854,480),fps).render(script,timeline,{'village':bg},video)
    clips.append(video)
listing=OUT/'concat.txt';listing.write_text(''.join("file '"+str(p)+"'\n" for p in clips))
video=OUT.parent/'character-motion-demo.mp4'
subprocess.run([ffmpeg_exe(),'-y','-v','error','-f','concat','-safe','0','-i',str(listing),'-c','copy','-movflags','+faststart',str(video)],check=True)
subprocess.run([ffmpeg_exe(),'-v','error','-i',str(video),'-f','null','-'],check=True)
print(video)
