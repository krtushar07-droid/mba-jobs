import urllib.request
import xml.etree.ElementTree as ET
import json

# RSS feed for Top Business News
FEED_URL = "https://economictimes.indiatimes.com/rssfeedstopstories.cms"
news_items = []

try:
    req = urllib.request.Request(FEED_URL, headers={'User-Agent': 'Mozilla/5.0'})
    xml_data = urllib.request.urlopen(req, timeout=15).read()
    root = ET.fromstring(xml_data)
    
    # Grab the top 15 news headlines
    for item in root.findall('./channel/item')[:15]:
        title = item.find('title').text
        link = item.find('link').text
        
        # Clean up the date string
        raw_date = item.find('pubDate').text if item.find('pubDate') is not None else ""
        clean_date = raw_date.replace("GMT", "").replace("+0530", "").strip()
        
        news_items.append({
            "title": title, 
            "source": "Economic Times", 
            "date": clean_date, 
            "url": link
        })
        
    with open("news.json", "w") as f:
        json.dump({"items": news_items}, f, indent=1)
        
    print(f"Successfully fetched {len(news_items)} news articles.")
except Exception as e:
    print("Could not fetch news:", e)
    # Create an empty file so the app doesn't crash
    with open("news.json", "w") as f:
        json.dump({"items": []}, f)
