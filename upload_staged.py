"""POST local files to Shopify staged-upload targets.
Usage: python3 upload_staged.py staged.json   (staged.json = stagedUploadsCreate response, any shape containing stagedTargets)
Each target's filename (last path part of resourceUrl) must exist in out/ or the project root.
Prints the resourceUrls that uploaded OK, for fileCreate / fileUpdate."""
import json, os, subprocess, sys
def find_targets(d):
    if isinstance(d, dict):
        if "stagedTargets" in d: return d["stagedTargets"]
        for v in d.values():
            t = find_targets(v)
            if t: return t
    return None
for t in find_targets(json.load(open(sys.argv[1]))):
    name = t["resourceUrl"].rsplit("/", 1)[-1]
    local = name
    if name.startswith("meta-sq-add-"): local = f"out_add/{name[len('meta-sq-add-'):-4]}.jpg"
    elif name.startswith("meta-sq-"): local = f"out/{name.split('-')[2]}.jpg"
    args = ["curl", "-s", "-o", "/dev/null", "-w", "%{http_code}", t["url"]]
    for p in t["parameters"]: args += ["-F", f"{p['name']}={p['value']}"]
    code = subprocess.run(args + ["-F", f"file=@{local}"], capture_output=True, text=True).stdout
    print(code, t["resourceUrl"])
