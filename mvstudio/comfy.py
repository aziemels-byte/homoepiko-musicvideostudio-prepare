"""Standard ComfyUI HTTP client. Modal is used through the EXISTING desktop bridge.
No Modal account/volume/code changes. Network writes require an explicit CLI flag.
"""
import json
import mimetypes
import urllib.request
import urllib.parse
import uuid
from pathlib import Path

class ComfyClient:
    def __init__(self, url="http://127.0.0.1:8188", timeout=30):
        self.url = url.rstrip("/")
        parsed = urllib.parse.urlparse(self.url)
        if parsed.scheme not in ("http", "https") or not parsed.netloc:
            raise ValueError("Invalid ComfyUI HTTP URL")
        self.timeout = timeout

    def _get(self, path):
        with urllib.request.urlopen(self.url + path, timeout=self.timeout) as r:
            return json.load(r)

    def system(self):
        return self._get("/system_stats")

    def queue(self):
        return self._get("/queue")

    def history(self, prompt_id):
        return self._get("/history/" + urllib.parse.quote(str(prompt_id)))

    def upload_image(self, path, folder="input"):
        path = Path(path)
        if not path.is_file():
            raise FileNotFoundError(path)
        boundary = "----MVSTUDIO" + uuid.uuid4().hex
        ctype = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        def form(name, data, filename=None, mime=None):
            line = f'--{boundary}\r\nContent-Disposition: form-data; name="{name}"'
            if filename:
                line += f'; filename="{filename}"'
            line += f'\r\nContent-Type: {mime or "text/plain"}'
            return (line + "\r\n\r\n").encode() + data + b"\r\n"
        body = form("image", path.read_bytes(), path.name, ctype) + form("type", folder.encode()) + f'--{boundary}--\r\n'.encode()
        req = urllib.request.Request(self.url + "/upload/image", data=body,
            headers={"Content-Type": f"multipart/form-data; boundary={boundary}"}, method="POST")
        with urllib.request.urlopen(req, timeout=max(self.timeout, 90)) as r:
            return json.load(r)

    def submit(self, api_graph, client_id=None):
        body = json.dumps({"prompt":api_graph, "client_id":client_id or str(uuid.uuid4())}).encode("utf-8")
        req = urllib.request.Request(self.url + "/prompt", body,
            {"Content-Type":"application/json"}, method="POST")
        with urllib.request.urlopen(req, timeout=self.timeout) as r:
            response = json.load(r)
        if not response.get("prompt_id"):
            raise RuntimeError("ComfyUI did not return a prompt_id: " + repr(response))
        return response
