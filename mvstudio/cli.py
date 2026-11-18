"""Local-first CLI: defaults never upload media or execute GPU work."""
import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from . import __version__
from . import workflow as wf
from .comfy import ComfyClient
from .plan import make_plan
from .qc import check as qc_check

ROOT = Path(__file__).resolve().parent.parent

def say(obj):
    print(json.dumps(obj,ensure_ascii=False,indent=2))

def safe_path(path):
    return Path(path).expanduser().resolve()

def add_arguments():
    p=argparse.ArgumentParser(prog="python -m mvstudio",description="Music Video Studio: Codex + ComfyUI/Modal + MVD + graphics")
    p.add_argument("--version", action="version",version=__version__)
    sub=p.add_subparsers(dest="cmd",required=True)
    dr=sub.add_parser("doctor",help="Local dependency checks; optional GET-only ComfyUI check")
    dr.add_argument("--comfy",action="store_true",help="GET-only probe of ComfyUI")
    dr.add_argument("--url",default="http://127.0.0.1:8188")
    ip=sub.add_parser("inspect",help="Show fields in UI/API workflow")
    ip.add_argument("workflow")
    mk=sub.add_parser("plan",help="Write the 26-shot editable scene plan (no generation)")
    mk.add_argument("--output",default=str(ROOT/"project"/"plan.json"))
    tm=sub.add_parser("timing",help="Analyze source audio into beat cues (local CPU, requires librosa)")
    tm.add_argument("--audio",default=str(ROOT/"assets"/"Homo_Epiko.mp3"))
    tm.add_argument("--output",default=str(ROOT/"project"/"beat_analysis.json"))
    pr=sub.add_parser("prepare",help="Generate ComfyUI UI shot variants from original source, no GPU")
    pr.add_argument("--workflow",default=str(ROOT/"source"/"video_ltx2_3_ia2v_ORIGINAL.json"))
    pr.add_argument("--plan",default=str(ROOT/"project"/"plan.json"))
    pr.add_argument("--output",default=str(ROOT/"project"/"generated_ui"))
    pr.add_argument("--audio-name",default="Homo_Epiko.mp3")
    pv=sub.add_parser("preview-api",help="Patch an already-exported API graph, save JSON only")
    pv.add_argument("--workflow",required=True)
    pv.add_argument("--mapping",required=True)
    pv.add_argument("--scene",type=int,required=True,help="1-based scene index")
    pv.add_argument("--image-name",required=True,help="Filename already inside ComfyUI input")
    pv.add_argument("--audio-name",default="Homo_Epiko.mp3")
    pv.add_argument("--plan",default=str(ROOT/"project"/"plan.json"))
    pv.add_argument("--output",required=True)
    sm=sub.add_parser("submit",help="Upload first-frame image and submit API prompt; DOUBLE OPT-IN")
    for action in pv._actions:
        if action.dest in ("workflow","mapping","scene","image_name","audio_name","plan"):
            if action.dest=="image_name":
                sm.add_argument("--image",required=True,help="Local PNG to upload via ComfyUI")
            elif action.dest in ("workflow","mapping"):
                sm.add_argument("--"+action.dest,required=True)
            elif action.dest=="scene":
                sm.add_argument("--scene",type=int,required=True)
            else:
                sm.add_argument("--"+action.dest.replace('_','-'),default=action.default)
    sm.add_argument("--url",default="http://127.0.0.1:8188")
    sm.add_argument("--execute",action="store_true",help="Actually submit to ComfyUI")
    sm.add_argument("--ack-target",choices=["I_VERIFIED_MODAL_WORKFLOW","I_ACCEPT_LOCAL_GENERATION"],
                    help="Mandatory confirmation of the API graph's compute route")
    sm.add_argument("--output",default=str(ROOT/"project"/"preview_submit.json"))
    stat=sub.add_parser("status",help="GET only: prompt history")
    stat.add_argument("--url",default="http://127.0.0.1:8188")
    stat.add_argument("--prompt-id",required=True)
    an=sub.add_parser("mvd",help="Delegate audio/scene analysis and EDL actions to upstream mvd CLI")
    an.add_argument("arguments",nargs=argparse.REMAINDER)
    edl=sub.add_parser("edl",help="Build Music Video Director EDL from scene renders")
    edl.add_argument("--plan",default=str(ROOT/"project"/"plan.json"))
    edl.add_argument("--renders",default=str(ROOT/"project"/"renders"))
    edl.add_argument("--audio",default=str(ROOT/"assets"/"Homo_Epiko.mp3"))
    edl.add_argument("--output",default=str(ROOT/"project"/"edit_plan.json"))
    qc=sub.add_parser("qc",help="FFprobe and dense review frames; no fake anatomy assessment")
    qc.add_argument("video")
    qc.add_argument("--out",required=True)
    qc.add_argument("--fps",type=int,default=8)
    co=sub.add_parser("composite",help="FFmpeg green screen + background composite (local CPU)")
    co.add_argument("--performance",required=True)
    co.add_argument("--background",required=True)
    co.add_argument("--audio",required=True)
    co.add_argument("--out",required=True)
    co.add_argument("--duration",type=float,required=True)
    co.add_argument("--audio-start",type=float,default=0.0,help="Song timeline offset in seconds")
    return p

def get_scene(file, n):
    plan=wf.load(file)
    if n<1 or n>len(plan["scenes"]): raise ValueError("Scene index out of range")
    return plan["scenes"][n-1]

def values_for_scene(scene, image_name, audio_name, mapping):
    vals={"prompt":scene["prompt"],"first_frame":image_name,
          "audio":audio_name,"audio_start":scene["start"],
          "duration":scene["duration"],"output_prefix":f"HomoEpiko/{scene['id']}"}
    required=("prompt","first_frame","audio","audio_start","duration")
    missing=[k for k in required if k not in mapping]
    if missing: raise ValueError("Incomplete API node mapping: " + ", ".join(missing))
    return {k:v for k,v in vals.items() if k in mapping}

def probe(path):
    p=subprocess.run(["ffprobe","-v","error","-show_entries","format=duration",
            "-of","default=noprint_wrappers=1:nokey=1",str(path)],text=True,capture_output=True)
    if p.returncode: raise RuntimeError(p.stderr.strip())
    return float(p.stdout.strip())

def main(argv=None):
    args=add_arguments().parse_args(argv)
    if args.cmd=="doctor":
        deps={k:shutil.which(k) for k in ("ffmpeg","ffprobe","git","node","ruby","mvd","claude")}
        deps["python"]=sys.executable
        report={"tools":deps,"local_workflow_exists":(ROOT/"source"/"video_ltx2_3_ia2v_ORIGINAL.json").exists(),
                "comfy_url":args.url,"comfy_probe":"skipped (use --comfy)"}
        if args.comfy:
            try:
                stats=ComfyClient(args.url).system()
                report["comfy_probe"]={"online":True,"devices":stats.get("devices",[])}
            except Exception as e:
                report["comfy_probe"]={"online":False,"error":str(e)}
        say(report)
    elif args.cmd=="inspect": say(wf.inspect(wf.load(args.workflow)))
    elif args.cmd=="plan":
        p=wf.dump(args.output,make_plan());say({"wrote":str(p),"scenes":26,"max_seconds":10,"status":"planned_only"})
    elif args.cmd=="timing":
        from .timing import analyze
        r=analyze(args.audio,args.output)
        say({"saved":args.output,"bpm_estimate":r["tempo_estimate"],"beats":len(r["beats"]),"duration":r["duration"]})
    elif args.cmd=="prepare":
        original=wf.load(args.workflow)
        if wf.kind(original)!="ui": raise ValueError("prepare requires original UI format")
        plan=wf.load(args.plan)
        out=Path(args.output);out.mkdir(parents=True,exist_ok=True)
        needs=[];ready=[]
        for i,s in enumerate(plan["scenes"]):
            image=s.get("first_frame") or "__REPLACE_WITH_SCENE_KEYFRAME.png"
            if image.startswith("__"):
                needs.append(s["id"])
            else:
                ready.append(s["id"])
            obj=wf.patch_ltx23_ui(original,prompt=s["prompt"],image=image,audio=args.audio_name,
                    start=s["start"],duration=s["duration"],prefix=f"video/HomoEpiko/{s['id']}",seed=637641141919248+i)
            wf.dump(out/f"{s['id']}_UI.json",obj)
        say({"written":len(ready)+len(needs),"files_in":str(out),
             "ready_if_assets_in_ComfyUI_input":ready,"need_unique_start_frame":needs,
             "note":"UI files are NOT executable via /prompt. Export each via ComfyUI API Format to submit."})
    elif args.cmd in ("preview-api","submit"):
        api=wf.load(args.workflow);mapping=wf.load(args.mapping)
        scene=get_scene(args.plan,args.scene)
        name=args.image_name if args.cmd=="preview-api" else Path(args.image).name
        values=values_for_scene(scene,name,args.audio_name,mapping)
        patched=wf.patch_api(api,mapping,values)
        wf.dump(args.output,patched)
        if args.cmd=="preview-api" or not args.execute:
            say({"saved":str(args.output),"execution":False,"note":"Submit requires --execute and --ack-target"})
            return
        if not args.ack_target: raise ValueError("Refusing GPU submission without --ack-target")
        # Explicit acknowledgement is REQUIRED; never guess that an LTX workflow uses Modal.
        client=ComfyClient(args.url)
        uploaded=client.upload_image(args.image)
        if not uploaded.get("name"):
            raise RuntimeError("ComfyUI upload did not return a filename")
        patched=wf.patch_api(api,mapping,values_for_scene(scene,uploaded["name"],args.audio_name,mapping))
        res=client.submit(patched)
        say({"execution":True,"prompt_id":res["prompt_id"],"scene":scene["id"],
             "compute_acknowledgement":args.ack_target,"url":args.url})
    elif args.cmd=="status": say(ComfyClient(args.url).history(args.prompt_id))
    elif args.cmd=="mvd":
        cmd=shutil.which("mvd")
        if not cmd:
            candidate=Path(sys.executable).parent/("mvd.exe" if os.name=="nt" else "mvd")
            if candidate.exists(): cmd=str(candidate)
        if not cmd: raise RuntimeError("mvd not installed: run bootstrap.ps1 -InstallDeps, or pip install -e vendor/music-video-director-skill")
        sys.exit(subprocess.call([cmd]+args.arguments))
    elif args.cmd=="edl":
        plan=wf.load(args.plan)
        dest=Path(args.renders);cuts=[];missing=[]
        for i,s in enumerate(plan["scenes"]):
            path=dest/(s["id"]+".mp4")
            if not path.is_file():
                missing.append(s["id"]);continue
            actual=probe(path)
            if actual+0.05<s["duration"]:
                raise ValueError(f"{s['id']} video shorter than required: {actual:.3f} < {s['duration']:.3f}")
            cuts.append({"n":i+1,"timeline_start":s["start"],"timeline_end":s["end"],
                 "source_file":str(path.resolve()),"source_in":0.0,"source_out":s["duration"],
                 "section":s["section"],"lyric":s["lyric_hint"],"description":s["prompt"]})
        if missing:
            say({"status":"incomplete","missing_video_assets":missing,"ready":len(cuts),
                 "note":"EDL not written: no fake coverage or filler"})
            return
        edl={"metadata":{"song_title":plan["title"],"total_duration":plan["duration"],
                        "total_cuts":len(cuts),"avg_shot_length":round(plan["duration"]/len(cuts),3)},
             "audio_file":str(Path(args.audio).resolve()),"output_file":str((Path(args.output).parent/"final.mp4").resolve()),
             "cuts":cuts}
        wf.dump(args.output,edl);say({"saved":str(args.output),"cuts":len(cuts),
              "next":"python -m mvstudio mvd validate project/edit_plan.json && python -m mvstudio mvd render project/edit_plan.json"})
    elif args.cmd=="qc":
        r=qc_check(args.video,args.out,args.fps)
        say({"review_frames":r["review_frames"],"technical_events":len(r["technical_events"]),
             "qc_report":str(Path(args.out)/"report.json"),"human_review_required":True})
    elif args.cmd=="composite":
        if not 0<args.duration<=10: raise ValueError("Duration must be <= 10 seconds for scene composite")
        bg=str(Path(args.background).resolve());fg=str(Path(args.performance).resolve());audio=str(Path(args.audio).resolve())
        for fp in (bg,fg,audio):
            if not Path(fp).is_file():raise FileNotFoundError(fp)
        out=str(Path(args.out).resolve());Path(out).parent.mkdir(parents=True,exist_ok=True)
        # Loop still background; video backgrounds use their original motion.
        is_img=Path(bg).suffix.lower() in (".png",".jpg",".jpeg",".webp")
        cmd=["ffmpeg","-hide_banner","-y"]
        if is_img:cmd += ["-loop","1","-framerate","24"]
        cmd += ["-i",bg,"-i",fg,"-ss",str(args.audio_start),"-i",audio,
             "-filter_complex","[0:v]fps=24,scale=1280:720:force_original_aspect_ratio=increase,crop=1280:720,setsar=1[bg];"
             "[1:v]fps=24,scale=1280:720,format=rgba,colorkey=0x00B140:0.22:0.08[fg];"
             "[bg][fg]overlay=x=0:y=0:shortest=1:format=auto,format=yuv420p[v]",
             "-map","[v]","-map","2:a:0","-t",str(args.duration),"-r","24",
             "-c:v","libx264","-crf","18","-preset","medium","-c:a","aac","-b:a","256k",out]
        p=subprocess.run(cmd,text=True,capture_output=True)
        if p.returncode:raise RuntimeError(p.stderr[-2500:])
        say({"wrote":out,"method":"CPU chromakey + background + master audio; no GPU job"})

if __name__=="__main__":
    try:main()
    except (ValueError,FileNotFoundError,RuntimeError,PermissionError) as e:
        print("ERROR:",e,file=sys.stderr);sys.exit(2)
