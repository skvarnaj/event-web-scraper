# scrapes event data from recreate 
import requests
from bs4 import BeautifulSoup
import re

URL = "https://luma.com/reccreatecollective"

def fetch_events():
    resp = requests.get(URL)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    events = []
    # In the page I saw each event title in an <h3> (###) tag in the snippet
    for h3 in soup.select("h3"):
        name = h3.get_text(strip=True)
        # Try to find a sibling element containing date/time
        # e.g., look at the next siblings or parent
        info = h3.find_next_sibling(text=True)
        date = None
        time = None
        if info:
            # crude pattern: look for something like “4:00 PM” or “Oct 12” etc
            time_match = re.search(r"\b\d{1,2}:\d{2}\s*(?:AM|PM)\b", info, re.IGNORECASE)
            date_match = re.search(r"\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\b.*\b\d{1,2}", info)
            if time_match:
                time = time_match.group(0)
            if date_match:
                date = date_match.group(0)
        events.append({"name": name, "date": date, "time": time})

    return events

if __name__ == "__main__":
    evts = fetch_events()
    for e in evts:
        print(f"Name: {e['name']}, Date: {e['date']}, Time: {e['time']}")