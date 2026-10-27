"""Independent read-only audit of the E-Waste split files."""
import hashlib, json, sys, collections, itertools
from pathlib import Path
from PIL import Image

ROOT = Path(sys.argv[1])
S = ROOT / "splits"
load = lambda p: [json.loads(l) for l in open(p) if l.strip()]

meta = {r["image_id"]: r for r in load(ROOT / "cleaned_images.jsonl")}
groups = json.load(open(S / "groups.json"))
img2grp = {}
for g in groups:
    for m in g["members"]:
        if m in img2grp: print("IMAGE IN TWO GROUPS", m)
        img2grp[m] = g["group_id"]
print("images in groups:", len(img2grp), "groups:", len(groups))

tasks = {}
for task in ["device_type", "external_condition"]:
    tasks[task] = {s: load(S / task / f"{s}.jsonl") for s in ["train", "validation", "test"]}

# 1. structural checks
for task, sp in tasks.items():
    print(f"\n== {task}")
    gsets = {}
    for s, rows in sp.items():
        ids = [r["image_id"] for r in rows]
        assert len(ids) == len(set(ids)), "dup image in split"
        bad_grp = [r for r in rows if img2grp.get(r["image_id"]) != r["group_id"]]
        missing = [r for r in rows if not (ROOT / r["image_path"]).exists()]
        meta_split = collections.Counter(meta[r["image_id"]]["new_split"] for r in rows)
        gsets[s] = {img2grp[i] for i in ids}
        print(s, len(rows), "groups", len(gsets[s]), "grp_mismatch", len(bad_grp),
              "missing", len(missing), "meta.new_split", dict(meta_split),
              "targets", dict(collections.Counter(r["target"] for r in rows)))
    for a, b in itertools.combinations(gsets, 2):
        print(f"group overlap {a}/{b}:", len(gsets[a] & gsets[b]))

# 2. image_id == sha256 of file? and pixel size / bytes per class (shortcut cues)
def dhash(path, size=8):
    im = Image.open(path).convert("L").resize((size + 1, size), Image.LANCZOS)
    px = list(im.getdata())
    bits = 0
    for y in range(size):
        for x in range(size):
            bits = (bits << 1) | (px[y * (size + 1) + x] > px[y * (size + 1) + x + 1])
    return bits

ec = tasks["external_condition"]
dt = tasks["device_type"]
all_rows = {r["image_id"]: (s, r) for s, rows in dt.items() for r in rows}
all_rows.update({r["image_id"]: (s, r) for s, rows in ec.items() for r in rows})
sha_bad = 0
info = {}
for iid, (s, r) in all_rows.items():
    p = ROOT / r["image_path"]
    b = p.read_bytes()
    if hashlib.sha256(b).hexdigest() != iid: sha_bad += 1
    with Image.open(p) as im:
        w, h = im.size; mode = im.mode; fmt = im.format
    info[iid] = dict(split=s, w=w, h=h, mode=mode, fmt=fmt, kb=len(b) / 1024, dh=dhash(p),
                     dt=r["device_type"], cond=r["external_condition"],
                     content=r.get("content_review"))
print("\nsha256 mismatches vs image_id:", sha_bad, "of", len(info))

# 3. cross-split near-dup check with plain dHash + flips (independent of their pHash)
def flips(path):
    im = Image.open(path)
    out = []
    for t in [None, Image.FLIP_LEFT_RIGHT, Image.ROTATE_90, Image.ROTATE_180, Image.ROTATE_270]:
        j = im if t is None else im.transpose(t)
        g = j.convert("L").resize((9, 8), Image.LANCZOS); px = list(g.getdata()); bits = 0
        for y in range(8):
            for x in range(8): bits = (bits << 1) | (px[y * 9 + x] > px[y * 9 + x + 1])
        out.append(bits)
    return out
train_h = [(iid, v["dh"]) for iid, v in info.items() if v["split"] == "train"]
hits = []
for iid, v in info.items():
    if v["split"] == "train": continue
    for fh in flips(ROOT / all_rows[iid][1]["image_path"]):
        for tid, th in train_h:
            d = bin(fh ^ th).count("1")
            if d <= 6: hits.append((v["split"], iid[:12], tid[:12], d, all_rows[iid][1]["image_path"], all_rows[tid][1]["image_path"]))
uniq = {(h[1], h[2]): h for h in hits}
print("eval-vs-train dHash near matches (<=6 bits):", len(uniq))
for h in sorted(uniq.values(), key=lambda x: x[3])[:30]: print("  ", h)

# 4. shortcut cues: per (device, condition, split) image size / bytes / source format
print("\n== external_condition per-class image properties")
def stats(rows):
    if not rows: return "-"
    ws = sorted(info[r["image_id"]]["w"] for r in rows); kb = sorted(info[r["image_id"]]["kb"] for r in rows)
    sq = sum(info[r["image_id"]]["w"] == info[r["image_id"]]["h"] for r in rows) / len(rows)
    sizes = collections.Counter((info[r["image_id"]]["w"], info[r["image_id"]]["h"]) for r in rows).most_common(2)
    return f"n={len(rows)} medW={ws[len(ws)//2]} medKB={kb[len(kb)//2]:.0f} square={sq:.0%} top={sizes}"
for s, rows in ec.items():
    for k in sorted({(r['device_type'], r['external_condition']) for r in rows}):
        sel = [r for r in rows if (r['device_type'], r['external_condition']) == k]
        print(s, k, stats(sel), dict(collections.Counter(r.get('content_review') for r in sel)))

# 5. provenance: source record id prefix / size per class (proxy for which raw dataset)
print("\n== train content_review by task")
for task in tasks:
    print(task, dict(collections.Counter((r["external_condition"], r.get("content_review")) for r in tasks[task]["train"])))
json.dump({k: {kk: vv for kk, vv in v.items()} for k, v in info.items()},
          open(Path(sys.argv[2]) / "audit_info.json", "w"))
