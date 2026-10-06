import json, re, os, datetime, urllib.request

INDIA_ONLY = True  # set False to keep jobs from all countries
GOOD = ["management trainee","trainee","associate","analyst","manager","strategy",
 "marketing","brand","product","consult","finance","operations","business",
 "sales","supply chain","hr ","human resources","mba","graduate","intern",
 "program","category","commercial","growth","partnership"]
BAD = ["engineer","developer","devops","sre","scientist","designer","technician",
 "driver","nurse","legal counsel","attorney"]
INDIA = ["india","bengaluru","bangalore","mumbai","delhi","gurgaon","gurugram",
 "noida","hyderabad","chennai","pune","kolkata","ahmedabad","remote"]

def get(url):
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 mba-jobs"})
        with urllib.request.urlopen(req, timeout=20) as r:
            return json.loads(r.read().decode("utf-8"))
    except Exception:
        return None

def slugs(name):
    n = name.lower().replace("&", " and ")
    plain = re.sub(r"[^a-z0-9]", "", n)
    dash = re.sub(r"[^a-z0-9]+", "-", n).strip("-")
    first = re.sub(r"[^a-z0-9]", "", n.split()[0])
    return list(dict.fromkeys([plain, dash, first]))

def greenhouse(s):
    d = get(f"https://boards-api.greenhouse.io/v1/boards/{s}/jobs")
    if not d or "jobs" not in d: return None
    return [{"id": f"gh{s}{j['id']}", "title": j["title"],
             "location": (j.get("location") or {}).get("name", ""),
             "url": j["absolute_url"]} for j in d["jobs"]]

def lever(s):
    d = get(f"https://api.lever.co/v0/postings/{s}?mode=json")
    if not isinstance(d, list): return None
    return [{"id": f"lv{s}{j['id']}", "title": j["text"],
             "location": (j.get("categories") or {}).get("location", "") or "",
             "url": j["hostedUrl"]} for j in d]

def fetch(c):
    tries = [c["slug"]] if c.get("slug") else slugs(c["name"])
    kinds = [c["ats"]] if c.get("ats") else ["greenhouse", "lever"]
    for s in tries:
        for k in kinds:
            r = greenhouse(s) if k == "greenhouse" else lever(s)
            if r: return r, f"{k}:{s}"
    return None, None

def relevant(j):
    t = j["title"].lower() + " "
    if any(b in t for b in BAD): return False
    if not any(g in t for g in GOOD): return False
    if INDIA_ONLY:
        loc = j["location"].lower()
        if loc and not any(i in loc for i in INDIA): return False
    return True

today = datetime.date.today().isoformat()
old = {}
if os.path.exists("jobs.json"):
    try:
        old = {j["id"]: j for j in json.load(open("jobs.json"))["jobs"]}
    except Exception:
        pass

companies = json.load(open("companies.json"))
jobs, found, missing = [], [], []
for c in companies:
    res, src = fetch(c)
    if res is None:
        missing.append(c["name"]); continue
    found.append(f"{c['name']} ({src})")
    for j in res:
        if relevant(j):
            j["company"], j["sector"] = c["name"], c.get("sector", "")
            j["first_seen"] = old.get(j["id"], {}).get("first_seen", today)
            j["new"] = j["first_seen"] == today
            jobs.append(j)

jobs.sort(key=lambda x: (not x["new"], x["company"]))
json.dump({"updated": today, "count": len(jobs), "jobs": jobs},
          open("jobs.json", "w"), indent=1)
json.dump({"found": found, "missing": missing},
          open("report.json", "w"), indent=1)
print(len(found), "companies read,", len(missing), "missing,", len(jobs), "jobs")
