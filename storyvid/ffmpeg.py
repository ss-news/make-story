"""Find a working ffmpeg: $FFMPEG, then the system one, then the binary bundled with imageio-ffmpeg."""
import os
import shutil
import subprocess
from functools import lru_cache


@lru_cache(maxsize=1)
def ffmpeg_exe() -> str:
    candidates = [os.environ.get("FFMPEG"), shutil.which("ffmpeg")]
    try:
        import imageio_ffmpeg
        candidates.append(imageio_ffmpeg.get_ffmpeg_exe())
    except ImportError:
        pass
    for exe in filter(None, candidates):
        if subprocess.run([exe, "-version"], capture_output=True).returncode == 0:
            return exe
    raise RuntimeError("No working ffmpeg found: pip install imageio-ffmpeg, or set FFMPEG=/path/to/ffmpeg")
