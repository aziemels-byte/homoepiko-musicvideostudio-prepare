"""Audio-derived timing cues. Requires librosa/numpy; no GPU or API calls."""
import json
from pathlib import Path

def analyze(path,output):
    import librosa
    import numpy as np
    y,sr=librosa.load(str(path),sr=11025,mono=True)
    percussive=librosa.effects.hpss(y)[1]
    tempo,beat_frames=librosa.beat.beat_track(y=percussive,sr=sr,hop_length=256,trim=False)
    beat_times=librosa.frames_to_time(beat_frames,sr=sr,hop_length=256)
    onset_env=librosa.onset.onset_strength(y=percussive,sr=sr,hop_length=256)
    beat_strengths=[float(onset_env[min(b,len(onset_env)-1)]) for b in beat_frames]
    peak=np.percentile(beat_strengths,95) if beat_strengths else 1
    result={"source":str(Path(path).resolve()),"duration":round(len(y)/sr,3),
            "tempo_estimate":round(float(np.atleast_1d(tempo)[0]),3),"method":"librosa beat_track on HPSS percussive audio, 11025Hz",
            "notes":"Tempo may be half/double. Beats and downbeats need ear/lyric verification.",
            "beats":[{"t":round(float(t),3),"strength":round(float(s)/max(peak,1e-6),3)}
                     for t,s in zip(beat_times,beat_strengths)]}
    Path(output).parent.mkdir(parents=True,exist_ok=True)
    Path(output).write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf8')
    return result
