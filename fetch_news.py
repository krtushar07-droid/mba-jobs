import json, re, html, time, os, datetime, urllib.request
import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime

# (category, source, feed url) - feeds that fail are skipped
FEEDS = [
 ("Markets", "Economic Times", "https://economictimes.indiatimes.com/markets/rssfeeds/1977021501.cms"),
 ("Startups", "Economic Times", "https://economictimes.indiatimes.com/small-biz/startups/rssfeeds/11993034.cms"),
 ("Economy", "Economic Times", "https://economictimes.indiatimes.com/news/economy/rssfeeds/1373380680.cms"),
 ("Markets", "Mint", "https://www.livemint.com/rss/markets"),
 ("Companies", "Mint", "https://www.livemint.com/rss/companies"),
 ("Economy", "Mint", "https://www.livemint.com/rss/economy"),
 ("Economy", "BusinessLine", "https://www.thehindubusinessline.com/economy/feeder/default.rss"),
 ("Companies", "BusinessLine", "https://www.thehindubusinessline.com/companies/feeder/default.rss"),
 ("Markets", "Business Standard", "https://www.business-standard.com/rss/markets-106.rss"),
 ("Companies", "Business Standard", "https://www.business-standard.com/rss/companies-101.rss"),
]
PER_FEED, MAX_ITEMS = 5, 30
UA = {"User-Agent": "Mozilla/5.0 (compatible; mba-jobs-news/1.0)"}
MEDIA = "{http://search.yahoo.com/mrss/}"
CONTENT = "{http://purl.org/rss/1.0/modules/content/}encoded"
report = {"ok": [], "failed": []}

def fetch(url, limit=400000):
    try:
        req = urllib.request.Request(url, headers=UA)
        with urllib.request.urlopen(req, timeout=20) as r:
            return r.read(limit)
    except Exception:
        return None

def clean(t):
    t = html.unescape(re.sub(r"<[^>]+>", " ", t or ""))
    return re.sub(r"\s+", " ", t).strip()

def trim(t, n=420):
    if len(t) <= n: return t
    return t[:n].rsplit(" ", 1)[0].rstrip(",;:") + "…"

def https(u):
    u = (u or "").strip()
    return "https://" + u[7:] if u.startswith("http://") else u

def meta(page, prop):
    for pat in (r'<meta[^>]+(?:property|name)=["\']%s["\'][^>]*content=["\']([^"\']*)["\']',
                r'<meta[^>]+content=["\']([^"\']*)["\'][^>]*(?:property|name)=["\']%s["\']'):
        m = re.search(pat % re.escape(prop), page, re.I)
        if m: return html.unescape(m.group(1)).strip()
    return ""

def feed_date(s):
    try: return parsedate_to_datetime(s)
    except Exception: pass
    try: return datetime.datetime.fromisoformat((s or "").replace("Z", "+00:00"))
    except Exception: return datetime.datetime.now(datetime.timezone.utc)

def feed_image(it, raw):
    for tag in (MEDIA + "content", MEDIA + "thumbnail"):
        for e in it.iter(tag):
            if e.get("url"): return e.get("url")
    for e in it.iter("enclosure"):
        if (e.get("type") or "").startswith("image") and e.get("url"): return e.get("url")
    m = re.search(r'<img[^>]+src=["\']([^"\']+)', raw or "", re.I)
    return m.group(1) if m else ""

items, seen = [], set()
for cat, src, url in FEEDS:
    data = fetch(url)
    try: root = ET.fromstring(data) if data else None
    except Exception: root = None
    if root is None:
        report["failed"].append(src + " " + cat); continue
    report["ok"].append(src + " " + cat)
    for it in list(root.iter("item"))[:PER_FEED]:
        title = clean(it.findtext("title"))
        link = (it.findtext("link") or "").strip()
        key = re.sub(r"\W+", "", title.lower())
        if not title or not link or key in seen: continue
        seen.add(key)
        desc_raw = it.findtext("description") or ""
        summary = clean(desc_raw) or clean(it.findtext(CONTENT))
        image = feed_image(it, desc_raw + (it.findtext(CONTENT) or ""))
        if len(summary) < 60 or not image:
            page = (fetch(link, 250000) or b"").decode("utf-8", "ignore")
            if page:
                if len(summary) < 60: summary = clean(meta(page, "og:description") or meta(page, "description")) or summary
                if not image: image = meta(page, "og:image")
            time.sleep(0.5)
        d = feed_date(it.findtext("pubDate") or it.findtext("date"))
        if d.tzinfo is None: d = d.replace(tzinfo=datetime.timezone.utc)
        items.append({"title": title, "source": src, "category": cat, "url": link,
                      "date": d.isoformat(), "summary": trim(summary), "image": https(image)})

items.sort(key=lambda x: x["date"], reverse=True)
items = items[:MAX_ITEMS]
if items or not os.path.exists("news.json"):
    json.dump({"updated": datetime.date.today().isoformat(), "items": items},
              open("news.json", "w"), indent=1, ensure_ascii=False)
print(len(items), "stories | feeds ok:", len(report["ok"]), "failed:", report["failed"])
print("with image:", sum(1 for i in items if i["image"]), "with summary:", sum(1 for i in items if i["summary"]))
