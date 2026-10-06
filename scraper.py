import json, re, os, time, hashlib, datetime, unicodedata
import urllib.request, urllib.parse

INDIA_ONLY = True
APP_ID = os.environ.get("ADZUNA_APP_ID", "")
APP_KEY = os.environ.get("ADZUNA_APP_KEY", "")
USE_ADZUNA = bool(APP_ID and APP_KEY)
USE_JOBSPY = os.environ.get("USE_JOBSPY", "1") == "1"

GOOD = ["management trainee","trainee","associate","analyst","manager","strategy",
 "marketing","brand","product","consult","finance","operations","business",
 "sales","supply chain","hr ","human resources","mba","graduate","intern",
 "program","category","commercial","growth","partnership"]
BAD = ["engineer","developer","devops","sre","scientist","designer","technician",
 "driver","nurse","legal counsel","attorney"]
INDIA = ["india","bengaluru","bangalore","mumbai","delhi","gurgaon","gurugram",
 "noida","hyderabad","chennai","pune","kolkata","ahmedabad","remote"]
ALIASES = {"EY":["ernst young"],"PwC":["pricewaterhousecoopers"],
 "Citi":["citibank","citigroup"],"Hindustan Unilever":["unilever"],
 "Nestle India":["nestle"],"Mahindra & Mahindra":["mahindra"],
 "Procter & Gamble":["p and g"],"Larsen & Toubro":["l and t"],
 "State Bank of India":["sbi"],"Tata Motors":["tata motors"]}
QUERIES = ["management trainee","MBA graduate","associate brand manager",
 "business analyst","strategy associate","marketing manager",
 "finance associate","operations manager","product manager","sales manager"]

errors = []

def get(url):
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 mba-jobs"})
        with urllib.request.urlopen(req, timeout=25) as r:
            return json.loads(r.read().decode("utf-8"))
    except Exception:
        return None

def s(x):
    if x is None or (isinstance(x, float) and x != x): return ""
    return str(x)

def words(t):
    t = unicodedata.normalize("NFKD", s(t)).encode("ascii", "ignore").decode().lower()
    return re.findall(r"[a-z0-9]+", t.replace("&", " and "))

def has(seq, sub):
    n = len(sub)
    return n > 0 and any(seq[i:i+n] == sub for i in range(len(seq) - n + 1))

def match(job_company, c):
    w = words(job_company)
    names = [c["name"]] + ALIASES.get(c["name"], [])
    return any(has(w, words(n)) for n in names)

# ---- Source 1: company career systems ----
def slugs(name):
    n = name.lower().replace("&", " and ")
    plain = re.sub(r"[^a-z0-9]", "", n)
    dash = re.sub(r"[^a-z0-9]+", "-", n).strip("-")
    first = re.sub(r"[^a-z0-9]", "", n.split()[0])
    return list(dict.fromkeys([plain, dash, first]))

def greenhouse(sl):
    d = get(f"https://boards-api.greenhouse.io/v1/boards/{sl}/jobs")
    if not d or "jobs" not in d: return None
    return [{"id": f"gh{sl}{j['id']}", "title": j["title"],
             "location": (j.get("location") or {}).get("name", ""),
             "url": j["absolute_url"]} for j in d["jobs"]]

def lever(sl):
    d = get(f"https://api.lever.co/v0/postings/{sl}?mode=json")
    if not isinstance(d, list): return None
    return [{"id": f"lv{sl}{j['id']}", "title": j["text"],
             "location": (j.get("categories") or {}).get("location", "") or "",
             "url": j["hostedUrl"]} for j in d]

def ats(c):
    tries = [c["slug"]] if c.get("slug") else slugs(c["name"])
    for sl in tries:
        for fn in (greenhouse, lever):
            r = fn(sl)
            if r: return r
    return None

# ---- Source 2: Adzuna India ----
def adzuna(c):
    q = urllib.parse.urlencode({"app_id": APP_ID, "app_key": APP_KEY,
        "results_per_page": 50, "what": c["name"], "max_days_old": 30,
        "sort_by": "date", "content-type": "application/json"})
    d = get(f"https://api.adzuna.com/v1/api/jobs/in/search/1?{q}")
    out = []
    for r in (d or {}).get("results", []):
        comp = (r.get("company") or {}).get("display_name", "")
        if not match(comp, c): continue
        out.append({"id": "adz" + s(r.get("id")),
            "title": re.sub(r"<[^>]+>", "", s(r.get("title"))),
            "location": (r.get("location") or {}).get("display_name", ""),
            "url": s(r.get("redirect_url"))})
    return out

# ---- Source 3: JobSpy (Indeed only) ----
def jobspy_all():
    try:
        from jobspy import scrape_jobs
    except Exception as e:
        errors.append("jobspy import: " + str(e)[:80]); return []
    rows = []
    for q in QUERIES:
        try:
            df = scrape_jobs(site_name=["indeed"], search_term=q,
                location="India", results_wanted=50, hours_old=24*14,
                country_indeed="India")
            rows += df.to_dict("records")
        except Exception as e:
            errors.append("jobspy " + q + ": " + str(e)[:80])
        time.sleep(2)
    return rows

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
    try: old = {j["id"]: j for j in json.load(open("jobs.json"))["jobs"]}
    except Exception: pass

companies = json.load(open("companies.json"))
seen, jobs = set(), []
by_src = {"company": 0, "adzuna": 0, "jobspy": 0}

def add(j, c, src):
    if not j["title"] or not j["url"] or not relevant(j): return
    key = (c["name"], j["title"].lower(), j["location"].lower())
    if key in seen: return
    seen.add(key)
    j["company"], j["sector"], j["src"] = c["name"], c.get("sector", ""), src
    j["first_seen"] = old.get(j["id"], {}).get("first_seen", today)
    j["new"] = j["first_seen"] == today
    jobs.append(j); by_src[src] += 1

for c in companies:
    res = ats(c)
    if res:
        for j in res: add(j, c, "company")
    elif USE_ADZUNA:
        for j in adzuna(c): add(j, c, "adzuna")
        time.sleep(0.4)

if USE_JOBSPY:
    for r in jobspy_all():
        comp = s(r.get("company"))
        for c in companies:
            if match(comp, c):
                url = s(r.get("job_url"))
                add({"id": "js" + hashlib.md5(url.encode()).hexdigest()[:12],
                     "title": s(r.get("title")), "location": s(r.get("location")),
                     "url": url}, c, "jobspy")
                break

found = sorted({j["company"] for j in jobs})
missing = [c["name"] for c in companies if c["name"] not in found]
if jobs or not old:
    jobs.sort(key=lambda x: (not x["new"], x["company"]))
    json.dump({"updated": today, "count": len(jobs), "jobs": jobs},
              open("jobs.json", "w"), indent=1)
else:
    errors.append("0 jobs found, kept yesterday's file")
json.dump({"found": found, "missing": missing, "by_source": by_src,
           "errors": errors[:20]}, open("report.json", "w"), indent=1)
print(len(found), "companies,", len(jobs), "jobs", by_src)
