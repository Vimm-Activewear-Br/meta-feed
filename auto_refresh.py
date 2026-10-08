"""Hourly, token-free refresh of the Meta feed. Runs in GitHub Actions (.github/workflows/refresh.yml).

Reads only public storefront data: the BAZAR collection (/collections/sale) and every product
(tags, variants, prices, photos). Refreshes state/bazar.json, re-applies state/rules.json, rebuilds the
CSV and status.json. The workflow commits and pushes whatever changed.

Things that need Claude (new products without square images, photos changed on Shopify) become
"ação" alerts on the dashboard and are sent once to Slack (#processos) and Todoist (project PROCESSOS)
when SLACK_WEBHOOK_URL / TODOIST_TOKEN are set. Stock isn't in this feed: Meta gets it live from Shopify."""
import json, os, subprocess, sys, urllib.request
from datetime import datetime
from fetch import get_json

os.chdir(os.path.dirname(os.path.abspath(__file__)))
STORE = "https://www.vimmactivewear.com"
DASHBOARD = "https://vimm-activewear-br.github.io/meta-feed/"
TODOIST_PROJECT = os.environ.get("TODOIST_PROJECT", "PROCESSOS")

def log(msg):
    with open("state/auto_refresh.log", "a") as f:
        f.write(f"{datetime.now():%Y-%m-%d %H:%M} {msg}\n")

def load(p, default):
    return json.load(open(p)) if os.path.exists(p) else default

def post(url, body, headers=None):
    req = urllib.request.Request(url, data=json.dumps(body).encode(), method="POST",
                                 headers={"Content-Type": "application/json", **(headers or {})})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r) if r.headers.get("Content-Type", "").startswith("application/json") else None

def slack(text):
    url = os.environ.get("SLACK_WEBHOOK_URL")
    if url: post(url, {"text": ("" if text.startswith("✅") else "<!here> ") + text})  # #processos has just the team: ping whoever is online

def todoist(content, description):
    token = os.environ.get("TODOIST_TOKEN")
    if not token: return
    auth = {"Authorization": f"Bearer {token}"}
    req = urllib.request.Request("https://api.todoist.com/api/v1/projects?limit=200", headers=auth)
    with urllib.request.urlopen(req, timeout=30) as r:
        projects = json.load(r).get("results", [])
    match = [p for p in projects if p["name"].strip().lower() == TODOIST_PROJECT.lower()]
    project_id = match[0]["id"] if match else post("https://api.todoist.com/api/v1/projects", {"name": TODOIST_PROJECT}, auth)["id"]
    # TODOIST_ASSIGNEES = e-mails (comma-separated) of people in the shared project. Todoist allows one
    # responsible per task, so each e-mail gets its own copy of the task; empty = one unassigned task.
    emails = [e.strip().lower() for e in os.environ.get("TODOIST_ASSIGNEES", "").split(",") if e.strip()]
    people = {}
    if emails:
        req = urllib.request.Request(f"https://api.todoist.com/api/v1/projects/{project_id}/collaborators", headers=auth)
        with urllib.request.urlopen(req, timeout=30) as r:
            people = {c["email"].lower(): c["id"] for c in json.load(r).get("results", [])}
    ids = []
    for uid in ([people.get(e) for e in emails if people.get(e)] or [None]):
        body = {"content": content, "description": description, "project_id": project_id}
        if uid: body["assignee_id"] = uid
        ids.append(post("https://api.todoist.com/api/v1/tasks", body, auth)["id"])
    return ids

def close_todoist(task_ids):
    token = os.environ.get("TODOIST_TOKEN")
    if not token: return
    for tid in task_ids:
        post(f"https://api.todoist.com/api/v1/tasks/{tid}/close", {}, {"Authorization": f"Bearer {token}"})

def notify_new_actions(alerts):
    """Each 'ação'/'erro' alert: sent once (Slack + Todoist, with the exact command for Claude).
    When it disappears (Claude did the work and pushed), its Todoist tasks are closed and Slack gets a ✅."""
    sent = load("state/notified.json", {})
    if isinstance(sent, list): sent = {t: {"todoist": []} for t in sent}
    current = {a["text"]: a for a in alerts if a["level"] in ("acao", "erro")}
    for text, a in current.items():
        if text in sent: continue
        cmd = a.get("command", "")
        try:
            slack(f"*Vimm · feed do Meta*: {text}\nCole no Claude (no Mac da Mariana):\n```{cmd}```\nPainel: {DASHBOARD}")
            ids = todoist(f"Feed do Meta: {text[:180]}", f"Cole no Claude (no Mac da Mariana):\n\n{cmd}\n\nPainel: {DASHBOARD}") or []
            sent[text] = {"todoist": ids}
        except Exception as e:
            log(f"falha ao avisar Slack/Todoist: {e!r}")
    for text in [t for t in sent if t not in current]:
        try:
            close_todoist(sent[text].get("todoist", []))
            slack(f"✅ Resolvido: {text}")
            log(f"aviso resolvido: {text}")
            del sent[text]
        except Exception as e:
            log(f"falha ao fechar aviso: {e!r}")
    json.dump(sent, open("state/notified.json", "w"), ensure_ascii=False, indent=1)

def main():
    bazar = sorted(str(p["id"]) for p in get_json(f"{STORE}/collections/sale/products.json?limit=250")["products"])
    old = load("state/bazar.json", {"ids": []})
    if bazar != old["ids"]:
        log(f"Bazar mudou: {sorted(set(old['ids']) ^ set(bazar))}")
        old["ids"] = bazar
        json.dump(old, open("state/bazar.json", "w"), indent=1)

    for script in ("refresh_products.py", "build_feed.py"):
        subprocess.run([sys.executable, script], check=True, capture_output=True, text=True)

    up = load("state/uploaded.json", {})
    not_on_fb = set(load("state/not_on_fb.json", {"ids": []})["ids"])
    scope = load("state/products.json", [])
    pending = [p["title"] for p in scope if p["id"] not in up and p["id"] not in not_on_fb and p["media"]]
    if pending != load("state/pending_new.json", []):
        json.dump(pending, open("state/pending_new.json", "w"), ensure_ascii=False, indent=1)
        if pending: log(f"produtos novos sem foto quadrada: {pending}")

    # Photos changed on a product we already squared → its squares are stale (redoing them needs Claude)
    now = {p["id"]: [m["url"].split("?")[0].rsplit("/", 1)[-1] for m in p["media"]] for p in scope if p["id"] in up}
    snap = load("state/images_snapshot.json", now)
    changed = [up[pid]["title"] for pid in now if pid in snap and now[pid] != snap[pid]]
    if changed: log(f"fotos alteradas na Shopify: {changed}")
    if now != snap or not os.path.exists("state/images_snapshot.json"):
        json.dump(now, open("state/images_snapshot.json", "w"), indent=0)
    flagged = sorted(set(load("state/photos_changed.json", [])) | set(changed))
    json.dump(flagged, open("state/photos_changed.json", "w"), ensure_ascii=False, indent=1)

    import status
    status.build(photo_changes=flagged)
    notify_new_actions(load("status.json", {}).get("alerts", []))

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        log(f"ERRO: {e!r}")
        try:
            import status
            status.build(errors=[f"Falha na verificação automática: {e!r}"[:300]])
            notify_new_actions(load("status.json", {}).get("alerts", []))
        except Exception:
            pass
        sys.exit(1)
