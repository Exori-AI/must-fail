"""Write diffs.json from your own video files: python3 extract.py out.json a.mp4 b.mp4 ...
Needs numpy and ffmpeg on PATH. Each frame is scaled to 64x112 RGB; diff[i] = mean |frame[i+1] - frame[i]|."""
import sys, json, subprocess, re, os
import numpy as np
W, H = 64, 112
out = {}
for f in sys.argv[2:]:
    p = subprocess.run(['ffmpeg', '-v', 'error', '-i', f, '-vf', f'scale={W}:{H}', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-'],
                       capture_output=True)
    a = np.frombuffer(p.stdout, np.uint8).reshape(-1, H, W, 3).astype(np.int16)
    d = np.abs(np.diff(a, axis=0)).mean(axis=(1, 2, 3))
    fps = float(re.search(r'([\d.]+) fps', subprocess.run(['ffmpeg', '-i', f], capture_output=True, text=True).stderr).group(1))
    out[os.path.basename(f)] = {'frames': len(a), 'fps': fps, 'dur_s': round(len(a) / fps, 2), 'diff': [round(float(x), 2) for x in d]}
json.dump(out, open(sys.argv[1], 'w'))
