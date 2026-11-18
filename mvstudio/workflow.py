"""Safe ComfyUI UI/API workflow inspectors and patchers.

Never silently convert a ComfyUI UI/subgraph export into an API prompt: Comfy's
frontend compiles widget inputs and nested subgraphs; a naive converter is unsafe.
"""
import copy
import json
from pathlib import Path


def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def dump(path, obj):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def kind(workflow):
    if isinstance(workflow, dict) and isinstance(workflow.get("nodes"), list):
        return "ui"
    if isinstance(workflow, dict) and workflow and all(
        isinstance(v, dict) and "class_type" in v and "inputs" in v for v in workflow.values()
    ):
        return "api"
    if isinstance(workflow, dict) and "prompt" in workflow:
        return kind(workflow["prompt"])
    raise ValueError("Unknown workflow shape: expected UI nodes[] or API {node_id:{class_type,inputs}}")


def inspect(workflow):
    typ = kind(workflow)
    if typ == "api":
        w = workflow.get("prompt", workflow)
        return {"kind": "api", "nodes": [
            {"id": k, "class_type": v["class_type"], "input_fields": list(v["inputs"].keys())}
            for k, v in w.items() if isinstance(v, dict)
        ]}
    return {"kind": "ui", "nodes": [
        {"id": n["id"], "class_type": n["type"],
         "widget_fields": list(n.get("widgets_values_named", {}).keys())}
        for n in workflow.get("nodes", [])],
        "subgraphs": len(workflow.get("definitions", {}).get("subgraphs", [])),
        "note": "UI workflow can be prepared/imported locally, but API queue requires ComfyUI's Export (API Format)."}


def set_widget(node, field, value, index):
    # Update both representations: Comfy frontend reads widgets_values arrays.
    named = node.get("widgets_values_named", {})
    if field not in named:
        raise ValueError(f"UI node {node['id']} lacks widget {field}")
    named[field] = value
    arr = node.get("widgets_values", [])
    if index >= len(arr):
        raise ValueError(f"UI node {node['id']} lacks widget index {index}")
    arr[index] = value


def patch_ltx23_ui(original, *, prompt, image, audio, start, duration, prefix, seed=None):
    """Patches the exact original LTX2.3 top-level UI graph without touching model nodes."""
    if kind(original) != "ui":
        raise ValueError("Expected UI workflow export")
    if not 0 < duration <= 10:
        raise ValueError("Scene duration must be in (0, 10] seconds")
    w = copy.deepcopy(original)
    nodes = {int(n["id"]): n for n in w["nodes"]}
    expected = {269: "LoadImage", 276: "LoadAudio", 341: "SaveVideo"}
    for nid, name in expected.items():
        if nid not in nodes or nodes[nid]["type"] != name:
            raise ValueError(f"This is not the verified source workflow: missing node {nid} ({name})")
    if 340 not in nodes or nodes[340]["type"] != "98ee9e5b-467b-40aa-a534-36033f27d0b4":
        raise ValueError("Not the verified LTX2.3 subgraph (node 340)")
    set_widget(nodes[269], "image", image, 0)
    set_widget(nodes[276], "audio", audio, 0)
    set_widget(nodes[340], "value", prompt, 0)
    set_widget(nodes[340], "start_index", round(float(start), 3), 4)
    set_widget(nodes[340], "value_4", round(float(duration), 3), 5)
    if seed is not None:
        set_widget(nodes[340], "noise_seed", int(seed), 7)
    set_widget(nodes[341], "filename_prefix", prefix, 0)
    return w


def patch_api(original, mapping, values):
    """Patch only explicitly mapped API inputs, leaving model/LoRA/sampler inputs unchanged.

    mapping example: {"prompt": {"node": "340", "input": "value"}, ...}
    """
    if kind(original) != "api":
        raise ValueError("API submission requires Export (API Format); a UI graph is NOT executable JSON")
    w = copy.deepcopy(original.get("prompt", original))
    for field, value in values.items():
        if value is None:
            continue
        target = mapping.get(field)
        if not target:
            raise ValueError(f"Missing explicit mapping for {field}")
        nid, name = str(target["node"]), str(target["input"])
        if nid not in w or name not in w[nid]["inputs"]:
            raise ValueError(f"Input mapping invalid: {field} -> {nid}.{name}")
        w[nid]["inputs"][name] = value
    return w
