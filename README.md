

# ComfyUI Saved Queue Tools

Two small, Windows-friendly CLI scripts for editing **ComfyUI Save/Load Queue** JSONs  
(requires the *comfyui-savequeues* node so you can export/import queues).


## Tools

### 1) `reframe_queue_and_prefixes.py`

Fixes the **video length** across both the executable graph and the UI metadata, and updates
`SaveVideo`/`SaveImage` filename prefixes so the `-###f` suffix matches the new frame count.

**What it touches**
- `EmptyHunyuanLatentVideo.inputs.length`
- `extra_pnginfo.workflow.nodes[].widgets_values[2]` (so the UI knob shows the new length)
- `SaveVideo`/`SaveImage.inputs.filename_prefix` → ensures a `-{frames}f` suffix

**Run (PowerShell/CMD)**
```bash
python ".\reframe_queue_and_prefixes.py" --file "C:\path\to\queue.json" --frames 145
````

Writes `queue.frames145.json` next to your input unless you pass `--out`.

**Example with explicit output**

```bash
python ".\reframe_queue_and_prefixes.py" ^
  --file "C:\queues\8-28-25 4070 14b.json" ^
  --frames 145 ^
  --out "C:\queues\OUT\8-28-25 4070 14b.FRAMES145.json"
```

---

### 2) `reseed_queue.py`

Batch-rewrites all `KSampler` `inputs.seed` values in a saved queue.
Supports **random** (repeatable with `--rng-seed`) and **increment** modes. Can limit to `queue_pending`.

**Dry-run first (prints changes, writes nothing)**

```bash
python ".\reseed_queue.py" --in "C:\queues\8-27-25.json" --out "C:\queues\OUT\reseeded.DRYRUN.json" --mode random --dry-run
```

**Random reseed (reproducible)**

```bash
python ".\reseed_queue.py" --in "C:\queues\8-27-25.json" --out "C:\queues\OUT\reseeded.RANDOM.json" --mode random --rng-seed 12345
```

**Increment – one counter across the whole queue**

```bash
python ".\reseed_queue.py" --in "C:\queues\8-27-25.json" --out "C:\queues\OUT\reseeded.INC_GLOBAL.json" --mode increment --start 600000 --step 1 --scope global
```

**Increment – restart counter per job**

```bash
python ".\reseed_queue.py" --in "C:\queues\8-27-25.json" --out "C:\queues\OUT\reseeded.INC_PERJOB.json" --mode increment --start 700000 --step 1 --scope job
```

**Only reseed `queue_pending`**

```bash
python ".\reseed_queue.py" --in "C:\queues\queue.json" --out "C:\queues\OUT\pending_only.json" --mode random --sections queue_pending
```

---

## Requirements

* Python 3.10+ (standard library only)
* ComfyUI with **Save/Load Queue Manager** and the **comfyui-savequeues** node

## Tips

* After writing a new JSON, **Load that file** in ComfyUI’s Save/Load Queue Manager.
* If the UI still shows the old frame length, you probably opened the old JSON.
  The reframe script patches the UI metadata, so the knob should change once you load the new file.


If anything else still looks off in preview, it’s almost always a missing closing code fence (```), mismatched backticks, or headings missing a blank line before/after.
````
