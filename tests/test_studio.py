import copy
import json
import tempfile
import unittest
from pathlib import Path
from mvstudio import workflow as wf
from mvstudio.plan import make_plan
from mvstudio.comfy import ComfyClient

ROOT=Path(__file__).resolve().parents[1]
class StudioTest(unittest.TestCase):
    def test_plan_26_full_coverage_under_ten(self):
        plan=make_plan();shots=plan['scenes']
        self.assertEqual(len(shots),26)
        self.assertEqual(shots[0]['start'],0)
        self.assertEqual(shots[-1]['end'],plan['duration'])
        for a,b in zip(shots, shots[1:]):
            self.assertEqual(a['end'],b['start'])
        self.assertTrue(all(0<x['duration']<=10 for x in shots))
    def test_ui_patch_preserves_model_lora_and_original(self):
        src=wf.load(ROOT/'source'/'video_ltx2_3_ia2v_ORIGINAL.json')
        before=copy.deepcopy(src)
        out=wf.patch_ltx23_ui(src,prompt='Dance performance',image='x.png',audio='song.mp3',
                   start=41.25,duration=7.1,prefix='test/S01',seed=88)
        self.assertEqual(src,before)
        orig={str(n['id']):n for n in src['nodes']};patched={str(n['id']):n for n in out['nodes']}
        for key in ('ckpt_name','lora_name','text_encoder','model_name','lora_name_1'):
            self.assertEqual(orig['340']['widgets_values_named'][key],patched['340']['widgets_values_named'][key])
        self.assertEqual(patched['340']['widgets_values_named']['start_index'],41.25)
        self.assertEqual(patched['340']['widgets_values'][5],7.1)
        self.assertEqual(patched['269']['widgets_values'][0],'x.png')
        self.assertEqual(patched['276']['widgets_values'][0],'song.mp3')
        self.assertEqual(patched['341']['widgets_values'][0],'test/S01')
    def test_reject_over_ten(self):
        src=wf.load(ROOT/'source'/'video_ltx2_3_ia2v_ORIGINAL.json')
        with self.assertRaises(ValueError):
            wf.patch_ltx23_ui(src,prompt='p',image='i',audio='a',start=0,duration=10.1,prefix='f')
    def test_api_requires_actual_api_export(self):
        src=wf.load(ROOT/'source'/'video_ltx2_3_ia2v_ORIGINAL.json')
        with self.assertRaises(ValueError):wf.patch_api(src,{}, {})
    def test_api_explicit_mapping_only(self):
        w={'11':{'class_type':'LoadImage','inputs':{'image':'a.png'}},
           '12':{'class_type':'Text','inputs':{'value':'old'}}}
        w2=wf.patch_api(w,{'prompt':{'node':'12','input':'value'}},{'prompt':'new'})
        self.assertEqual(w2['12']['inputs']['value'],'new')
        self.assertEqual(w['12']['inputs']['value'],'old')
        with self.assertRaises(ValueError):wf.patch_api(w,{}, {'prompt':'abc'})
        with self.assertRaises(ValueError):wf.patch_api(w,{'prompt':{'node':'999','input':'x'}},{'prompt':'abc'})
    def test_api_patch_with_five_required_fields(self):
        from mvstudio.cli import values_for_scene
        from mvstudio.plan import make_plan
        scene=make_plan()['scenes'][0]
        mapping={k:{'node':str(i+1),'input':'x'} for i,k in enumerate(('prompt','first_frame','audio','audio_start','duration'))}
        vals=values_for_scene(scene,'image.png','audio.mp3',mapping)
        self.assertEqual(vals['duration'],scene['duration'])
        self.assertEqual(vals['first_frame'],'image.png')
        self.assertEqual(vals['audio_start'],0)
        with self.assertRaises(ValueError):values_for_scene(scene,'image.png','audio.mp3',{'prompt':{'node':'1','input':'x'}})

    def test_comfy_mock_http_submission(self):
        from http.server import BaseHTTPRequestHandler,HTTPServer
        import threading
        calls=[]
        class Fake(BaseHTTPRequestHandler):
            def log_message(self,*a):pass
            def do_GET(self):
                b=b'{"devices":[]}'
                self.send_response(200);self.send_header('Content-Length',str(len(b)));self.end_headers();self.wfile.write(b)
            def do_POST(self):
                length=int(self.headers['Content-Length']);data=self.rfile.read(length)
                calls.append(json.loads(data))
                b=b'{"prompt_id":"dry-test-id"}'
                self.send_response(200);self.send_header('Content-Length',str(len(b)));self.end_headers();self.wfile.write(b)
        server=HTTPServer(('127.0.0.1',0),Fake)
        thr=threading.Thread(target=server.serve_forever,daemon=True);thr.start()
        try:
            client=ComfyClient(f'http://127.0.0.1:{server.server_port}')
            self.assertEqual(client.system()['devices'],[])
            res=client.submit({'1':{'class_type':'Test','inputs':{'value':'test'}}})
            self.assertEqual(res['prompt_id'],'dry-test-id')
            self.assertEqual(calls[0]['prompt']['1']['inputs']['value'],'test')
        finally:
            server.shutdown();server.server_close();thr.join(timeout=2)

    def test_comfy_client_validates_url(self):
        for u in ('file:///etc/passwd','/prompt',''):
            with self.assertRaises(ValueError):ComfyClient(u)

if __name__=='__main__':unittest.main()
