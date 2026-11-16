import json, os, re, html, urllib.request

LIST_URL = "https://www.sainsburys.jobs/jobs/?location=southampton"
BASE = "https://www.sainsburys.jobs"
KEYWORDS = ["portswood", "burgess"]
SEEN_FILE = "seen.json"
TOPIC = os.environ["NTFY_TOPIC"]
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; job-watcher)"}

def get(url):
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read().decode("utf-8", "ignore")

def text_of(page):
    page = re.sub(r"(?is)<(script|style).*?</\1>", " ", page)
    page = re.sub(r"(?s)<[^>]+>", " ", page)
    return re.sub(r"\s+", " ", html.unescape(page))

def notify(title, message, url=None, priority="high"):
    headers = {"Title": title, "Priority": priority, "Tags": "briefcase"}
    if url:
        headers["Click"] = url
    req = urllib.request.Request(
        f"https://ntfy.sh/{TOPIC}", data=message.encode("utf-8"),
        headers=headers, method="POST")
    urllib.request.urlopen(req, timeout=30)

page = get(LIST_URL)
ids = sorted(set(re.findall(r"/jobs/description/(\d+)", page)))

if os.environ.get("MANUAL") == "true":
    notify("Job watcher is running",
           f"Test OK. {len(ids)} Southampton jobs listed right now.",
           priority="default")

if os.path.exists(SEEN_FILE):
    seen = set(json.load(open(SEEN_FILE)))
    first_run = False
else:
    seen, first_run = set(ids), True

if not first_run:
    for i in ids:
        if i in seen:
            continue
        url = f"{BASE}/jobs/description/{i}/"
        try:
            detail = text_of(get(url))
        except Exception:
            continue  # retry next run
        pos = page.find(i)
        card = text_of(page[max(0, pos - 1500):pos + 300])
        combined = (card + " " + detail).lower()
        if any(k in combined for k in KEYWORDS):
            hours = re.findall(r"\d+(?:\.\d+)?\s*hours?[^.]{0,40}", detail, re.I)[:3]
            hours_txt = " | ".join(hours) if hours else "hours not found - check the listing"
            notify("NEW Sainsbury's job: Portswood/Burgess", hours_txt, url)
        seen.add(i)

json.dump(sorted(seen), open(SEEN_FILE, "w"))
