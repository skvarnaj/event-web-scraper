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
            "journalingclasses": (self.parse_luma_general, "@journalingclasses", "https://luma.com/journalingclasses"), # TODO add in year check date on this
            # craft nook only shows past events
            #"craftnook": (self.parse_luma_general, "Craft Nook", "https://lu.ma/craftnook?period=past")


            # gcal sites
            "cleos": (self.parse_cleos, "Cleo's Yarn Shop", "https://cleosyarnshop.com/pages/events-calendar"),

            # other sites
            "okofarms": (self.parse_okofarms, "Oko Farms", "https://www.okofarms.org/eventsstackedev"),
            "farmone": (self.parse_farmone, "Farm.One", "https://farm.one/farm-one-events/"),
            "susanalexandra": (self.parse_susan_alexandra, "Susan Alexandra", "https://www.susanalexandra.com/collections/events")
        }

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
                        "Date": current_date,
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
        return all_data