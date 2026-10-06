import json, re, urllib.request

URL = "https://gray-moss-0eae35510.5.azurestaticapps.net/api/updates"

try:
    req = urllib.request.Request(URL, headers={"User-Agent": "mba-jobs"})
    d = json.loads(urllib.request.urlopen(req, timeout=30).read().decode("utf-8"))
except Exception as e:
    print("Could not fetch updates:", e)
    raise SystemExit(0)

def clean(body):
    out = []
    for line in str(body).replace("\r", "").split("\n"):
        if re.search(r"unsubscribe|opt.?out|track\.appspot|Sender notified|\[image", line, re.I):
            continue
        out.append(line)
    t = re.sub(r"\n{3,}", "\n\n", "\n".join(out)).strip()
    return t[:2500]

# Grabs all items without filtering by "approved" status
items = [{"title": x.get("title", ""), "body": clean(x.get("body", "")),
          "sent": x.get("sent") or ""}
         for x in d.get("items", [])]
         
items.sort(key=lambda x: x["sent"], reverse=True)
json.dump({"items": items[:100]}, open("updates.json", "w"), indent=1)
print(len(items), "total updates saved")
