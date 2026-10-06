import json, urllib.request

# Your live Google Script Web App URL:
URL = "https://script.google.com/macros/s/AKfycbwyrBSBDRWxABjiBynjY7nCf4wScHALeezOQlQL8mOFLEbKpVVqjPCDsJN3KNkos2Zf/exec"

try:
    # Fetch the JSON data directly from your Google Script
    response = urllib.request.urlopen(URL, timeout=30).read().decode("utf-8")
    data = json.loads(response)
    
    # This automatically creates/updates the updates.json file
    with open("updates.json", "w") as f:
        json.dump({"items": data.get("items", [])}, f, indent=1)
        
    print("Successfully pulled notices from Google Script.")
except Exception as e:
    print("Could not fetch updates:", e)
    raise SystemExit(0)
