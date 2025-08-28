#!/usr/bin/env python3

import argparse, json, os, sys, random
from typing import Any, Dict, Iterable, List, Tuple

KSAMPLER_CLASSES = {
    "KSampler",
    "KSamplerAdvanced",
    "KSampler (Efficient)",
    "KSamplerSDXL",
    "KSamplerTiled",
    "SamplerCustom",
}

def iter_queue_items(doc: Dict[str, Any], which: Iterable[str] = ("queue_running","queue_pending")):
    """Yield (section_name, index_in_section, queue_item) for each item."""
    for section in which:
        items = doc.get(section, [])
        if not isinstance(items, list):
            continue
        for idx, item in enumerate(items):
            # Expect item like [priority/int, job_id/str, nodes_dict, outputs?]
            if isinstance(item, list) and len(item) >= 3 and isinstance(item[2], dict):
                yield section, idx, item
            else:
                # Some tools might store dicts directly
                if isinstance(item, dict):
                    yield section, idx, item

def iter_nodes_from_item(item: Any) -> Iterable[Tuple[str, Dict[str, Any]]]:
    """Yield (node_id, node_obj) for each node in a queue item, best-effort across common formats."""
    # Standard Save/Load Queue item: [prio, uuid, nodes_dict, ...]
    if isinstance(item, list) and len(item) >= 3 and isinstance(item[2], dict):
        nodes = item[2]
        for nid, node in nodes.items():
            if isinstance(node, dict):
                yield str(nid), node
    # Fallback: item is itself a nodes dict (rare), e.g. {"3":{...},...}
    elif isinstance(item, dict):
        for nid, node in item.items():
            if isinstance(node, dict):
                yield str(nid), node

def find_seed_fields(node: Dict[str, Any]) -> List[Tuple[List[str], int]]:
    """Return list of ([path_keys], current_seed_int) for all seed-like fields we intend to edit.
       Currently: node['inputs']['seed'] when class_type is in KSAMPLER_CLASSES.
    """
    out = []
    cls = node.get("class_type")
    if cls in KSAMPLER_CLASSES:
        ins = node.get("inputs", {})
        if isinstance(ins, dict) and "seed" in ins:
            try:
                val = int(ins["seed"])
                out.append((["inputs","seed"], val))
            except Exception:
                pass
    return out

def apply_seed(node: Dict[str, Any], path: List[str], new_seed: int) -> None:
    cur = node
    for k in path[:-1]:
        if isinstance(cur, dict) and k in cur:
            cur = cur[k]
        else:
            return
    last = path[-1]
    if isinstance(cur, dict) and last in cur:
        cur[last] = int(new_seed)

def reseed_document(doc: Dict[str, Any], mode: str, *, start: int = 0, step: int = 1,
                    scope: str = "global", rng_seed: int = None,
                    only_sections: List[str] = None) -> Tuple[int,int]:
    """Reseed in place. Returns (nodes_touched, seeds_changed)."""
    rnd = random.Random(rng_seed) if rng_seed is not None else random.Random()
    nodes_touched = 0
    seeds_changed = 0
    seq_val = start

    valid_sections = ("queue_running","queue_pending") if not only_sections else tuple(only_sections)
    # If scope is per-job, we reset seq_val at each job
    for section, idx, item in iter_queue_items(doc, which=valid_sections):
        job_seed = start
        def next_seq():
            nonlocal seq_val, job_seed
            if scope == "job":
                v = job_seed
                job_seed += step
                return v
            else:
                v = seq_val
                seq_val += step
                return v

        for nid, node in iter_nodes_from_item(item):
            fields = find_seed_fields(node)
            if not fields:
                continue
            nodes_touched += 1
            for path, cur_seed in fields:
                if mode == "random":
                    new_seed = rnd.randint(0, 2_147_483_647)
                elif mode == "increment":
                    new_seed = next_seq()
                else:
                    raise ValueError("Unknown mode: %r" % mode)
                if int(new_seed) != int(cur_seed):
                    apply_seed(node, path, new_seed)
                    seeds_changed += 1
    return nodes_touched, seeds_changed

def main():
    ap = argparse.ArgumentParser(description="Reseed ComfyUI Save/Load Queue JSON (KSampler seeds).")
    ap.add_argument("--in", dest="input_path", required=True, help="Path to input queue JSON")
    ap.add_argument("--out", dest="output_path", required=True, help="Where to write the reseeded JSON")
    ap.add_argument("--mode", choices=["random","increment"], required=True, help="Reseed mode")
    ap.add_argument("--start", type=int, default=0, help="[increment] starting seed (default 0)")
    ap.add_argument("--step", type=int, default=1, help="[increment] step between seeds (default 1)")
    ap.add_argument("--scope", choices=["global","job"], default="global",
                    help="[increment] global => count across the whole queue; job => restart per job")
    ap.add_argument("--rng-seed", type=int, default=None, help="[random] Python RNG seed for reproducibility")
    ap.add_argument("--sections", nargs="*", default=None,
                    help="Only reseed these sections (default: queue_running queue_pending)")
    ap.add_argument("--dry-run", action="store_true", help="Parse and report without writing")
    args = ap.parse_args()

    with open(args.input_path, "r", encoding="utf-8") as f:
        doc = json.load(f)

    nodes_touched, seeds_changed = reseed_document(
        doc, args.mode, start=args.start, step=args.step, scope=args.scope,
        rng_seed=args.rng_seed, only_sections=args.sections
    )

    print(f"Nodes touched: {nodes_touched}, seed fields changed: {seeds_changed}")

    if not args.dry_run:
        # Ensure output directory exists
        os.makedirs(os.path.dirname(os.path.abspath(args.output_path)), exist_ok=True)
        with open(args.output_path, "w", encoding="utf-8") as f:
            json.dump(doc, f, indent=2)
        print(f"Wrote: {args.output_path}")
    else:
        print("Dry run; no file written.")

if __name__ == "__main__":
    main()
