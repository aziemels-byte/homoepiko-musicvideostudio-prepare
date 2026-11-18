# HomoEpiko MusicVideoStudio

This repository exports the Python workflow preparation tools, offline tests and example inputs from the existing HomoEpiko MusicVideoStudio project at commit `0814b9e6efac5c72d91e40d5d5b2ea719d5bcddb`. It includes a ComfyUI workflow with placeholder media names and a p5 effect. Original media, model weights, credentials and rendering outputs are kept separately.

Run the baseline checks from the repository root on Linux with Python 3.12 and Node.js 22.

```sh
python3 -m unittest discover -s tests -v
out="$(mktemp -d)"
python3 -m mvstudio prepare --plan project/plan.json --output "$out"
find "$out" -maxdepth 1 -type f -name '*.json' | wc -l
node --check effects/homo_epiko_world.p5.js
```

The reference plan creates 26 JSON workflows. These checks use no GPU. See [third-party notices](THIRD_PARTY_NOTICES.md) for the upstream graph attribution.
