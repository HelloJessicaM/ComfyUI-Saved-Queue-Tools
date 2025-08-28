# reframe_queue_and_prefixes.py
import argparse, json, os, re
from copy import deepcopy

def rewrite_prefix(prefix: str, frames: int) -> str:
    """Ensure the prefix contains '-{frames}f' (replace existing '-###f' if present)."""
    if not isinstance(prefix, str):
        return prefix
    # Replace existing '-###f' just before optional 'steps' or end
    new = re.sub(r'-(\d+)f(?=(\d+steps)?$)', f'-{frames}f', prefix)
    if new == prefix:
        # If there wasn't a -###f segment, append one
        new = f"{prefix}-{frames}f"
    return new

def fix_graph_nodes(graph_dict: dict, frames: int):
    for node in graph_dict.values():
        # 1) Set length on EmptyHunyuanLatentVideo
        if node.get("class_type") == "EmptyHunyuanLatentVideo":
            inputs = node.setdefault("inputs", {})
            inputs["length"] = int(frames)

        # 2) Rewrite filename_prefix on SaveVideo / SaveImage
        if node.get("class_type") in ("SaveVideo", "SaveImage"):
            inputs = node.setdefault("inputs", {})
            if "filename_prefix" in inputs:
                inputs["filename_prefix"] = rewrite_prefix(inputs["filename_prefix"], frames)

def fix_workflow_nodes(meta: dict, frames: int):
    """
    In extra_pnginfo.workflow.nodes[], mirror the UI knobs:
      - EmptyHunyuanLatentVideo: widgets_values = [w, h, length, batch]
      - SaveVideo/SaveImage: widgets_values[0] = filename_prefix
    """
    wf = meta.get("extra_pnginfo", {}).get("workflow")
    if not isinstance(wf, dict):
        return
    nodes = wf.get("nodes")
    if not isinstance(nodes, list):
        return

    for n in nodes:
        ntype = n.get("type")
        wv = n.get("widgets_values")
        # EmptyHunyuanLatentVideo length sits at index 2
        if ntype == "EmptyHunyuanLatentVideo" and isinstance(wv, list) and len(wv) >= 3:
            wv[2] = int(frames)
        # SaveVideo / SaveImage first widget is filename_prefix
        if ntype in ("SaveVideo", "SaveImage") and isinstance(wv, list) and len(wv) >= 1:
            if isinstance(wv[0], str):
                wv[0] = rewrite_prefix(wv[0], frames)

def fix_job_entry(job_entry, frames: int):
    """
    Each job looks like: [number, uuid, GRAPH_DICT, META_DICT, [...outputs...]]
    We touch index 2 (graph) and index 3 (meta) if present.
    """
    if not isinstance(job_entry, list):
        return
    # Graph dict at index 2
    if len(job_entry) >= 3 and isinstance(job_entry[2], dict):
        fix_graph_nodes(job_entry[2], frames)
    # Meta dict at index 3
    if len(job_entry) >= 4 and isinstance(job_entry[3], dict):
        fix_workflow_nodes(job_entry[3], frames)

def process_saved_queue(data: dict, frames: int):
    # Known queues to traverse
    for key in ("queue_running", "queue_pending", "queue_failed"):
        arr = data.get(key)
        if isinstance(arr, list):
            for job in arr:
                fix_job_entry(job, frames)
    return data

def main():
    ap = argparse.ArgumentParser(description="Adjust frames and filename prefixes in a ComfyUI saved queue JSON.")
    ap.add_argument("--file", required=True, help="Path to the saved queue JSON")
    ap.add_argument("--frames", type=int, default=145, help="Target frame length (default: 145)")
    ap.add_argument("--out", help="Optional explicit output path (defaults to <stem>.frames{N}.json)")
    args = ap.parse_args()

    in_path = args.file
    out_path = args.out
    frames = int(args.frames)

    with open(in_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    updated = process_saved_queue(deepcopy(data), frames)

    if not out_path:
        base, ext = os.path.splitext(in_path)
        out_path = f"{base}.frames{frames}{ext or '.json'}"

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(updated, f, indent=2, ensure_ascii=False)

    print(f"✅ Wrote: {out_path}")

if __name__ == "__main__":
    main()
