import re
import pytz
import requests
from datetime import datetime
from playwright.async_api import async_playwright

class CraftScraper:
    def __init__(self):
        # We now map names to a tuple: (the parser function, the organization name, the URL)
        self.registry = {
            # luma sites
            "recreate": (self.parse_luma_general, "ReCreate Collective", "https://lu.ma/reccreatecollective"),
            "mojo": (self.parse_luma_general, "Mojo Studios", "https://luma.com/mojostudio"),
            "artgurl": (self.parse_luma_general, "Art Gurl", "https://luma.com/artgurl"),
            "journalingclasses": (self.parse_luma_general, "@journalingclasses", "https://luma.com/journalingclasses"),
            
            # craft nook only shows past events
            #"craftnook": (self.parse_luma_general, "Craft Nook", "https://lu.ma/craftnook?period=past")

            # gcal sites
            "cleos": (self.parse_cleos, "Cleo's Yarn Shop", "https://cleosyarnshop.com/pages/events-calendar"),
            "teastand": (self.parse_theteastand, "The Tea Stand", "https://www.theteastand.org/calendar/"),

            # other sites
            "okofarms": (self.parse_okofarms, "Oko Farms", "https://www.okofarms.org/eventsstackedev"),
            "farmone": (self.parse_farmone, "Farm.One", "https://farm.one/farm-one-events/"),
            "susanalexandra": (self.parse_susan_alexandra, "Susan Alexandra", "https://www.susanalexandra.com/collections/events"),
            "craft_society": (self.parse_craftsociety, "Craft Society", "https://www.craft-society.com/event-list"),
            "recess_grove": (self.parse_square_booking, "Recess Grove", "https://book.squareup.com/classes/ug7iad378g5yho/location/LR3E6CBQNN96A/classes"),
            "lucky_risograph": (self.parse_lucky_risograph, "Lucky Risograph", "https://luckyrisograph.press/riso-foundation-group"),
            "artshack": (self.parse_artshack, "Artshack Brooklyn", "https://www.artshackbrooklyn.org/events/events"),
        }

    def ensure_year(self, date_str):
        if not date_str or date_str == "TBD":
            return date_str
            
        # Regex looks for any 4-digit year starting with 20 (e.g., 2025, 2026)
        if not re.search(r'202\d', date_str):
            # If no year found, append 2026. 
            # We add a comma for better formatting if it looks like "Jan 5"
            return f"{date_str.strip()}, 2026"
        
        return date_str
    
    def update_public_index(self):
        # Create the HTML rows from your registry
        list_items = ""
        for key in self.registry:
            _, org_name, url = self.registry[key]
            list_items += f'            <li><a href="{url}" target="_blank">{org_name}</a></li>\n'

        html_content = f"""<!DOCTYPE html>
                <html lang="en">
                <head>
                    <meta charset="UTF-8">
                    <meta name="viewport" content="width=device-width, initial-scale=1.0">
                    <title>Tracked Craft Organizations</title>
                    <style>
                        body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 40px auto; padding: 0 20px; }}
                        h1 {{ color: #222; border-bottom: 2px solid #f0f0f0; padding-bottom: 10px; }}
                        ul {{ list-style: none; padding: 0; }}
                        li {{ background: #fafafa; margin: 10px 0; padding: 15px; border-radius: 8px; border: 1px solid #eee; transition: transform 0.2s; }}
                        li:hover {{ transform: translateX(5px); border-color: #007bff; }}
                        a {{ text-decoration: none; color: #007bff; font-weight: 600; display: block; }}
                        .footer {{ margin-top: 40px; font-size: 0.8em; color: #888; text-align: center; }}
                    </style>
                </head>
                <body>
                    <h1>Tracked Organizations</h1>
                    <p>Currently monitoring {len(self.registry)} sites for new workshops:</p>
                    <ul>
                {list_items}
                    </ul>
                    <div class="footer">Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M')}</div>
                </body>
                </html>"""

        # Write the file to your VS Code workspace
        with open("index.html", "w", encoding="utf-8") as f:
            f.write(html_content)
        print("✅ index.html has been updated in your folder.")

    async def parse_luma_general(self, org_name, url):
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            await page.goto(url)
            
            # Scroll to trigger lazy-loading
            for _ in range(5): 
                await page.mouse.wheel(0, 2000)
                await page.wait_for_timeout(600)

            await page.wait_for_selector("h3", timeout=10000)

            # Advanced JavaScript Extraction (The logic you already verified)
            elements_data = await page.evaluate("""() => {
                const results = [];
                const nodes = document.querySelectorAll('h3, .date');
                nodes.forEach(node => {
                    let foundTime = "TBD";
                    if (node.tagName === 'H3') {
                        let container = node.parentElement;
                        for(let i=0; i<3; i++) { 
                            if(container && container.parentElement) container = container.parentElement;
                        }
                        const containerText = container ? container.innerText : "";
                        const timeMatch = containerText.match(/\\d{1,2}:\\d{2}\\s*[ap]m/i);
                        if (timeMatch) foundTime = timeMatch[0];
                    }
                    results.push({
                        tagName: node.tagName,
                        className: node.className,
                        innerText: node.innerText,
                        time: foundTime
                    });
                });
                return results;
            }""")

            events = []
            current_date = "TBD"

            for el in elements_data:
                text = el['innerText'].strip()
                if "date" in el['className'].lower():
                    current_date = text
                elif el['tagName'] == "H3":
                    events.append({
                        "Organization": org_name,
                        "Event": text,
                        "Date": self.ensure_year(current_date),
                        "Time": el['time'],
                        "URL": url
                    })

            await browser.close()
            return events
        
    async def parse_cleos(self, org_name, url):
        calendar_id = "c_6c7f0ee51f9122edb3a0eb5cc32a20ffb03ddb3e246905182053f8a6f81e289c@group.calendar.google.com"
        ical_url = f"https://calendar.google.com/calendar/ical/{calendar_id}/public/basic.ics"
        
        try:
            response = requests.get(ical_url)
            if response.status_code != 200:
                return []
            
            # Google folds long lines; join them back together
            content = response.text.replace("\r\n ", "")
            events = []
            local_tz = pytz.timezone("America/New_York")
            
            raw_events = content.split("BEGIN:VEVENT")
            
            for block in raw_events[1:]:
                title_match = re.search(r"SUMMARY:(.*)", block)
                time_match = re.search(r"DTSTART[:;](?:VALUE=DATE:)?(\d{8}T\d{6}Z|\d{8})", block)
                
                if title_match and time_match:
                    title = title_match.group(1).replace('\\', '').strip()
                    raw_time = time_match.group(1).strip()
                    
                    if 'T' in raw_time:
                        utc_dt = datetime.strptime(raw_time, "%Y%m%dT%H%M%SZ").replace(tzinfo=pytz.UTC)
                        local_dt = utc_dt.astimezone(local_tz)
                        
                        # Added %Y for the year
                        event_date = local_dt.strftime("%a, %b %d, %Y")
                        event_time = local_dt.strftime("%I:%M %p").lstrip('0')
                        compare_date = local_dt.date()
                    else:
                        date_obj = datetime.strptime(raw_time, "%Y%m%d")
                        event_date = date_obj.strftime("%a, %b %d, %Y")
                        event_time = "All Day"
                        compare_date = date_obj.date()

                    if compare_date >= datetime.now(local_tz).date():
                        events.append({
                            "Organization": org_name,
                            "Event": title,
                            "Date": event_date,
                            "Time": event_time,
                            "URL": url
                        })
            
            # Sort chronologically (including the year in the parse)
            events.sort(key=lambda x: datetime.strptime(x['Date'], "%a, %b %d, %Y"))
            return events

        except Exception as e:
            print(f"Extraction error: {e}")
            return []
    
    async def parse_okofarms(self, org_name, url):
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            await page.goto(url)
            
            # Squarespace event lists often take a second to render
            await page.wait_for_selector("article, .eventlist-event", timeout=10000)

            events_data = await page.evaluate("""() => {
                const results = [];
                const eventItems = document.querySelectorAll('article, .eventlist-event');
                
                eventItems.forEach(item => {
                    const titleEl = item.querySelector('h1, h2, .eventlist-title');
                    const dateEl = item.querySelector('.eventlist-dateline, time, .eventlist-meta-date');
                    
                    if (titleEl) {
                        results.push({
                            // Use .trim() in JavaScript, not .strip()
                            title: titleEl.innerText.trim(), 
                            dateTimeBlock: dateEl ? dateEl.innerText.trim() : "TBD"
                        });
                    }
                });
                return results;
            }""")

            events = []
            for item in events_data:
                # Squarespace usually puts date and time on separate lines or with a pipe |
                # We'll split by newline or pipe to try and get clean columns
                raw_block = item['dateTimeBlock'].replace('|', '\n')
                parts = [p.strip() for p in raw_block.split('\n') if p.strip()]
                
                raw_date = parts[0] if len(parts) > 0 else "TBD"
                raw_time = parts[1] if len(parts) > 1 else "TBD"

                events.append({
                    "Organization": org_name,
                    "Event": item['title'],
                    "Date": raw_date,
                    "Time": raw_time,
                    "URL": url
                })

            await browser.close()
            return events
        
    async def parse_farmone(self, org_name, url):
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            await page.goto(url, wait_until="networkidle")
            await page.wait_for_selector('body')

            events_data = await page.evaluate("""() => {
                const results = [];
                // Look for containers that have a "BOOK" button
                const eventBlocks = Array.from(document.querySelectorAll('div')).filter(el => 
                    el.innerText.includes('BOOK')
                );

                const seenTitles = new Set();

                eventBlocks.forEach(block => {
                    const lines = block.innerText.split('\\n').map(l => l.trim()).filter(l => l.length > 0);
                    
                    if (lines.length >= 2) {
                        const title = lines[0];
                        const dateTimeLine = lines[1];

                        // Ensure we haven't processed this title and the line looks like a date
                        if (dateTimeLine.match(/[A-Z][a-z]+ \d{1,2}, \d{4}/) && !seenTitles.has(title)) {
                            results.push({
                                title: title,
                                rawText: dateTimeLine
                            });
                            seenTitles.add(title);
                        }
                    }
                });
                return results;
            }""")

            events = []
            for item in events_data:
                raw_info = item['rawText']
                
                # 1. Clean the Time: Use regex to find "7:00pm" or "10:30am" 
                # and ignore anything after it (like "More info" or "$20")
                time_search = re.search(r'(\d{1,2}:\d{2}(?:am|pm|AM|PM))', raw_info)
                time_val = time_search.group(1) if time_search else "Check Site"

                # 2. Clean the Date: Extract everything before the time
                date_search = re.search(r'([A-Z][a-z]+ \d{1,2}, \d{4})', raw_info)
                date_val = date_search.group(1) if date_search else raw_info

                events.append({
                    "Organization": org_name,
                    "Event": item['title'],
                    "Date": date_val,
                    "Time": time_val,
                    "URL": url
                })

            await browser.close()
            return events
        
    async def parse_susan_alexandra(self, org_name, url):
        json_url = "https://www.susanalexandra.com/collections/events/products.json"
        
        try:
            response = requests.get(json_url)
            if response.status_code != 200:
                return []
            
            data = response.json()
            events = []
            today = datetime.now()
            
            for product in data.get('products', []):
                title = product.get('title')
                handle = product.get('handle')
                product_url = f"https://www.susanalexandra.com/products/{handle}"
                
                for variant in product.get('variants', []):
                    variant_title = variant.get('title') 
                    
                    # 1. Separate Date and Time
                    # Looks for patterns like "6-8:30pm" or "6pm"
                    time_match = re.search(r'(\d{1,2}(?::\d{2})?\s?[-–]\s?\d{1,2}(?::\d{2})?(?:am|pm))', variant_title, re.IGNORECASE)
                    
                    if time_match:
                        event_time = time_match.group(1).strip()
                        raw_date = variant_title[:time_match.start()].strip()
                    else:
                        event_time = "Check Site"
                        raw_date = variant_title.strip()

                    # 2. Smart Year & Explicit Formatting
                    # Remove "Wednesday" (if they typed it) and "st/nd/rd/th"
                    clean_date = re.sub(r'(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday|st|nd|rd|th|,)', '', raw_date, flags=re.IGNORECASE).strip()
                    
                    try:
                        # Parse the month and day (e.g., "January 21")
                        # We assume current year initially
                        date_obj = datetime.strptime(f"{clean_date} {today.year}", "%B %d %Y")
                        
                        # ROLLOVER LOGIC: If the date is earlier in the year than today, it must be 2026
                        if date_obj < today:
                            date_obj = date_obj.replace(year=today.year + 1)
                        
                        # EXPLICIT FORMAT: Day, Month Day, Year
                        event_date = date_obj.strftime("%A, %B %d, %Y")
                    except Exception as e:
                        # Fallback: if parsing fails, just tack the logical year onto their text
                        current_month_val = today.month
                        # Simple check: if month is Jan (1) and today is Dec (12), it's next year
                        event_date = f"{raw_date}, 2026" if "jan" in raw_date.lower() else f"{raw_date}, 2025"

                    events.append({
                        "Organization": org_name,
                        "Event": title,
                        "Date": event_date,
                        "Time": event_time,
                        "URL": product_url
                    })
            
            return events

        except Exception as e:
            print(f"Shopify Smart-Year Error: {e}")
            return []
    
    async def parse_theteastand(self, org_name, url):
        # We use the direct embed URL for the most stable HTML structure
        embed_url = "https://calendar.google.com/calendar/u/0/embed?src=c40f9cfe3d861c76ac9855f5cbb8fd444b41fb2c647bd979fa70bf687fed008a@group.calendar.google.com&mode=AGENDA"
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            
            # This context forces the browser to New York time even if you're in PST
            context = await browser.new_context(
                timezone_id="America/New_York",
                locale="en-US",
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )
            page = await context.new_page()
            
            try:
                await page.goto(embed_url, wait_until="networkidle")
                # Wait for the main event container class
                await page.wait_for_selector('.ryakYc', timeout=15000)

                events_data = await page.evaluate("""() => {
                    const results = [];
                    const rows = document.querySelectorAll('.ryakYc');
                    
                    rows.forEach(row => {
                        // Title is in the URIUGf class
                        const titleEl = row.querySelector('.URIUGf');
                        const title = titleEl ? titleEl.innerText.trim() : "";
                        
                        // Time is in the dIVgne class
                        const timeEl = row.querySelector('.dIVgne');
                        const time = timeEl ? timeEl.innerText.trim() : "All Day";

                        // Get the button with the full aria-label for date extraction
                        const btn = row.querySelector('[role="button"]');
                        const label = btn ? btn.getAttribute('aria-label') : "";
                        
                        // REGEX: Extracts "January 10, 2026" from the long label string
                        const dateMatch = label.match(/(January|February|March|April|May|June|July|August|September|October|November|December)\s\d{1,2},\s202\d/);
                        const dateStr = dateMatch ? dateMatch[0] : "TBD";
                        
                        if (title) {
                            results.push({ title, time, date: dateStr });
                        }
                    });
                    return results;
                }""")

                events = []
                for item in events_data:
                    # Pass the date through your ensure_year helper
                    final_date = self.ensure_year(item['date'])
                    
                    events.append({
                        "Organization": org_name,
                        "Event": item['title'],
                        "Date": final_date,
                        "Time": item['time'],
                        "URL": "https://www.theteastand.org/calendar/"
                    })

                await browser.close()
                return events

            except Exception as e:
                print(f"Tea Stand Extraction error: {e}")
                await browser.close()
                return []
    async def parse_craftsociety(self, org_name, url):
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                timezone_id="America/New_York",
                locale="en-US",
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )
            page = await context.new_page()
            
            try:
                await page.goto(url, wait_until="networkidle")
                # Increased timeout to ensure all items load
                await page.wait_for_selector('li', timeout=20000)

                events_data = await page.evaluate("""() => {
                    const results = [];
                    
                    // 1. Find the "Past Events" marker
                    const allHeadings = Array.from(document.querySelectorAll('h1, h2, h3, h4, p, span, strong'));
                    const pastMarker = allHeadings.find(el => el.innerText.trim().toLowerCase().includes('past events'));

                    // 2. Get all potential event items
                    const items = Array.from(document.querySelectorAll('li'));
                    
                    items.forEach(item => {
                        // STOP CONDITION: If this item is located AFTER the "Past Events" marker, skip it.
                        if (pastMarker && (pastMarker.compareDocumentPosition(item) & Node.DOCUMENT_POSITION_FOLLOWING)) {
                            return; 
                        }

                        const text = item.innerText.trim();
                        // Basic filter to ensure it's a date-carrying event
                        if (text.length > 10 && (text.includes('Jan') || text.includes('Feb') || text.includes('Mar'))) {
                            let title = "";
                            let datePart = "";
                            
                            if (text.includes(':')) {
                                const parts = text.split(':');
                                title = parts[0].trim();
                                datePart = parts.slice(1).join(':').trim();
                            } else if (text.includes('.')) {
                                const parts = text.split('.');
                                title = parts[0].trim();
                                datePart = parts[1].trim();
                            } else {
                                title = text;
                            }
                            results.push({ title, datePart });
                        }
                    });
                    return results;
                }""")

                events = []
                for item in events_data:
                    # 1. Clean out newlines
                    raw_title = item['title'].replace('\n', ' ').strip()
                    full_raw_text = f"{raw_title} {item['datePart']}".replace('\n', ' ').strip()

                    # 2. Extract specific date pattern (Day, Month Date)
                    # Stops matching before extra text like "Craft Society" or "Come mend"
                    date_pattern = r'\b(Sun|Mon|Tue|Wed|Thu|Fri|Sat)[a-z]*,\s+(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{1,2}'
                    date_match = re.search(date_pattern, full_raw_text, re.IGNORECASE)
                    
                    if date_match:
                        clean_date = date_match.group(0)
                        clean_title = full_raw_text[:date_match.start()].strip()
                    else:
                        clean_date = item['datePart']
                        clean_title = raw_title

                    # Cleanup title punctuation
                    clean_title = clean_title.rstrip(':.- ')
                    
                    # Append year helper
                    final_date = self.ensure_year(clean_date)

                    events.append({
                        "Organization": org_name,
                        "Event": clean_title,
                        "Date": final_date,
                        "Time": "Check Website",
                        "URL": url
                    })
                
                await browser.close()
                return events

            except Exception as e:
                print(f"Craft Society Extraction Error: {e}")
                await browser.close()
                return []
    async def parse_square_booking(self, org_name, url):
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                timezone_id="America/New_York",
                locale="en-US"
            )
            page = await context.new_page()
            
            try:
                await page.goto(url, wait_until="networkidle")
                # Wait for the main content area
                await page.wait_for_selector('h2, li', timeout=20000)

                events_data = await page.evaluate("""() => {
                    const results = [];
                    let current_date = "";
                    
                    // Get every element that could be a date header or an event item
                    const elements = document.querySelectorAll('h2, li, [role="listitem"]');
                    
                    elements.forEach(el => {
                        const text = el.innerText.trim();
                        
                        // 1. Check if this element is a Date Header (e.g., "Saturday, January 24, 2026")
                        if (el.tagName === 'H2' || el.classList.contains('heading-20')) {
                            if (text.includes('202')) { // Look for the year to confirm it's a date
                                current_date = text;
                            }
                        } 
                        
                        // 2. If it's a list item and we have a current_date, it's an event
                        else if (el.tagName === 'LI' || el.getAttribute('role') === 'listitem') {
                            if (text.toLowerCase().includes('am') || text.toLowerCase().includes('pm')) {
                                results.push({
                                    title: text.split('\\n')[0].trim(), // Take first line as title
                                    raw_info: text,
                                    date: current_date
                                });
                            }
                        }
                    });
                    return results;
                }""")

                events = []
                for item in events_data:
                    # Cleanup the Title (Square often puts price/duration in the text)
                    # "Basket Weaving 2 hrs $50" -> "Basket Weaving"
                    clean_title = item['title'].split('$')[0].strip()
                    
                    # Cleanup the Time (Find "10:30 AM" in the text)
                    time_match = re.search(r'\d{1,2}:\d{2}\s*(?:am|pm|AM|PM)', item['raw_info'])
                    clean_time = time_match.group(0).lower().replace(' ', '') if time_match else "Check Site"

                    # Cleanup the Date (Remove the Day of Week prefix if you want it identical to others)
                    # "Saturday, January 24, 2026" -> "Jan 24, 2026"
                    raw_date = item['date']
                    date_match = re.search(r'(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{1,2}', raw_date)
                    clean_date = date_match.group(0) if date_match else raw_date

                    events.append({
                        "Organization": org_name,
                        "Event": clean_title,
                        "Date": self.ensure_year(clean_date),
                        "Time": clean_time,
                        "URL": url
                    })
                
                await browser.close()
                return events

            except Exception as e:
                print(f"Square Sticky Header Error: {e}")
                await browser.close()
                return []
    async def parse_lucky_risograph(self, org_name, url):
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                timezone_id="America/New_York",
                locale="en-US",
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )
            page = await context.new_page()
            
            try:
                # Standardized timeout for third-party widgets
                await page.goto(url, wait_until="load", timeout=60000)
                
                # Essential delay for the Acuity/booking container to populate
                await page.wait_for_timeout(10000)

                events = []
                
                # Search all frames for the event text
                for frame in page.frames:
                    try:
                        frame_text = await frame.evaluate("() => document.body.innerText")
                        if not frame_text: 
                            continue

                        lines = frame_text.split('\n')
                        current_date = "TBD"

                        for line in lines:
                            line = line.strip()
                            if not line: 
                                continue

                            # Capture Date Header (Looks for year and month)
                            if "202" in line and any(m in line for m in ["Jan", "Feb", "Mar"]):
                                current_date = line
                            
                            # Capture Time Slot
                            if ":" in line and ("am" in line.lower() or "pm" in line.lower()):
                                # Using re (pre-imported in your environment)
                                date_match = re.search(r'(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{1,2}', current_date, re.I)
                                
                                if date_match:
                                    raw_match = date_match.group(0)
                                    # Normalize to "Jan 24" format
                                    clean_date = f"{raw_match[:3]} {raw_match.split()[-1]}"
                                else:
                                    clean_date = current_date

                                events.append({
                                    "Organization": org_name,
                                    "Event": "Riso Foundation: Group Workshop",
                                    "Date": self.ensure_year(clean_date),
                                    "Time": line.lower().replace(' ', ''),
                                    "URL": url
                                })
                    except:
                        continue

                await browser.close()
                return events

            except Exception as e:
                await browser.close()
                return []
    async def parse_artshack(self, org_name, url):
        import re
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            
            try:
                # Go to the events page
                await page.goto(url, wait_until="networkidle", timeout=60000)
                
                # Wait for the Webflow dynamic items to render
                await page.wait_for_selector(".content-wrapper-featured", timeout=10000)
                
                events = []
                # Target the "Current & upcoming" section items
                items = await page.query_selector_all(".content-wrapper-featured")
                
                for item in items:
                    # 1. Get the Title
                    title_el = await item.query_selector(".heading-3")
                    title = await title_el.inner_text() if title_el else ""
                    
                    # 2. Get the Date/Time blocks
                    dt_elements = await item.query_selector_all(".time-date-text")
                    
                    raw_date = "TBD"
                    raw_time = "TBD"
                    
                    # Only collect visible text
                    texts = []
                    for el in dt_elements:
                        if await el.is_visible():
                            texts.append(await el.inner_text())

                    if texts:
                        # Extract the first visible block (usually the date)
                        primary_text = texts[0].strip()
                        
                        # Fix the "Sat Jan 31 - Sun Feb 1st1pm to 4pm" issue
                        # If a time marker (like '1pm' or '1 pm') is stuck to the date:
                        if re.search(r'\d\s?(am|pm)', primary_text.lower()):
                            # Split at the first digit that is followed by am/pm
                            split_match = re.split(r'(\d+\s?(?:am|pm))', primary_text, flags=re.IGNORECASE)
                            raw_date = split_match[0].strip()
                            # Reconstruct the time from the remaining parts
                            raw_time = "".join(split_match[1:]).lower().replace(' ', '').replace('to', ' - ')
                        else:
                            raw_date = primary_text

                        # If time wasn't pulled from the first block, check the second block
                        if raw_time == "TBD" and len(texts) >= 2:
                            raw_time = texts[1].lower().replace(' ', '').replace('to', ' - ')

                    # 3. Final Cleaning
                    if title and raw_date != "TBD":
                        # Remove ordinal suffixes (1st, 2nd, 3rd, 4th) so the date parser is happy
                        clean_date_str = re.sub(r'(\d+)(st|nd|rd|th)', r'\1', raw_date)
                        
                        # Handle date ranges (take the first date only for filtering)
                        if "-" in clean_date_str:
                            clean_date_str = clean_date_str.split("-")[0].strip()

                        events.append({
                            "Organization": org_name,
                            "Event": title.strip(),
                            "Date": self.ensure_year(clean_date_str),
                            "Time": raw_time,
                            "URL": url
                        })

                await browser.close()
                return events

            except Exception as e:
                print(f"Artshack error: {e}")
                await browser.close()
                return []
    
    async def run_all(self):
        all_data = []
        for name, (parser_func, org_label, url) in self.registry.items():
            try:
                print(f"Scraping {org_label}...")
                # Pass the org name and URL directly to the general parser
                site_events = await parser_func(org_label, url)
                all_data.extend(site_events)
            except Exception as e:
                print(f"Error scraping {name}: {e}")

        self.update_public_index()
        return all_data