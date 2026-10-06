import json, re, urllib.request

URL = "https://gray-moss-0eae35510.5.azurestaticapps.net/api/updates"
API_KEY = "Tk9xR2mQ7vLp4Zc8WnB3yHd6Jf5Sa1"

try:
    # We add the x-api-key header that your Google Script revealed
    req = urllib.request.Request(URL, headers={
        "User-Agent": "mba-jobs-scraper",
        "x-api-key": API_KEY
    })
    response = urllib.request.urlopen(req, timeout=30).read().decode("utf-8")
    d = json.loads(response)
except Exception as e:
    print("Could not fetch updates from Azure:", e)
    raise SystemExit(0)

def clean(body):
    out = []
    for line in str(body).replace("\r", "").split("\n"):
        if re.search(r"unsubscribe|opt.?out|track\.appspot|Sender notified|\[image", line, re.I):
            continue
        out.append(line)
    t = re.sub(r"\n{3,}", "\n\n", "\n".join(out)).strip()
    return t[:2500]

# Handle the data whether it comes back as a list or a dictionary
raw_items = d if isinstance(d, list) else d.get("items", [])

items = []
for x in raw_items:
    # Google Script uses 'subject' and 'date', so we capture those
    title = x.get("title") or x.get("subject") or "Placement Notice"
    body = clean(x.get("body", ""))
    sent = x.get("sent") or x.get("date") or ""
    items.append({"title": title, "body": body, "sent": sent})
         
items.sort(key=lambda x: x["sent"], reverse=True)

with open("updates.json", "w") as f:
    json.dump({"items": items[:100]}, f, indent=1)
    
print(f"Successfully pulled {len(items)} notices from Azure API.")
