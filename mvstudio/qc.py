"""Mechanical QC and review frames: cannot certify face or anatomy correctness."""
import json
import re
import subprocess
from pathlib import Path

def run(cmd):
    p=subprocess.run(cmd,text=True,capture_output=True)
    if p.returncode:
        raise RuntimeError((p.stderr or p.stdout)[-1800:])
    return p

def check(video, output, sample_fps=8):
    video=Path(video).resolve()
    output=Path(output)
    output.mkdir(parents=True,exist_ok=True)
    p=run(["ffprobe","-v","error","-print_format","json","-show_entries",
           "format=duration:stream=codec_type,width,height,avg_frame_rate,nb_frames",str(video)])
    media=json.loads(p.stdout)
    # Sample frames without inventing a deformation detector.
    run(["ffmpeg","-hide_banner","-loglevel","error","-y","-i",str(video),
         "-vf",f"fps={sample_fps},scale=640:-2","-q:v","4",str(output/"frame_%05d.jpg")])
    p=subprocess.run(["ffmpeg","-hide_banner","-i",str(video),
                      "-vf","blackdetect=d=0.15:pix_th=0.10,freezedetect=n=-50dB:d=0.5",
                      "-an","-f","null","-"],text=True,capture_output=True)
    incidents=[line.strip() for line in p.stderr.splitlines() if ("black_start:" in line or "freeze_start:" in line or "freeze_end:" in line)]
    report={"source":str(video),"format":media.get("format",{}),"streams":media.get("streams",[]),
            "sample_fps":sample_fps,"review_frames":len(list(output.glob('frame_*.jpg'))),
            "technical_events":incidents,"human_review_required":[
               "Check EVERY critical movement and face/head rotation in dense frame strips",
               "Check hands, feet, anatomy, continuity and transitions frame by frame",
               "Listen against the master song; auto beat detection is NOT proof of synchronization"]}
    (output/"report.json").write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding='utf-8')
    return report
