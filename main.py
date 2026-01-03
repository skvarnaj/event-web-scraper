import os
import asyncio
import pandas as pd
from datetime import datetime
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from scraper import CraftScraper
from dotenv import load_dotenv

# This looks for the .env file and loads the variables
load_dotenv()

# Now access it using os.getenv
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")

# --- CONFIGURATION ---
SENDER_EMAIL = "jnskvarna@gmail.com"
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")
RECEIVER_EMAIL = "jnskvarna@gmail.com"

async def send_email(df):
    msg = MIMEMultipart()
    msg['From'] = SENDER_EMAIL
    msg['To'] = RECEIVER_EMAIL
    msg['Subject'] = f"✨ Upcoming Events!"

    # Generate the HTML table from Pandas
    # 'table_id' allows us to target it specifically with CSS
    html_table = df.to_html(index=False, escape=False, table_id="event-table")
    
    # Modern Aesthetic CSS
    style = """
    <style>
        #event-table {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            border-collapse: collapse;
            width: 100%;
            max-width: 850px; /* Slightly wider to accommodate date */
            margin: 20px 0;
            font-size: 14px;
            box-shadow: 0 4px 8px rgba(0,0,0,0.05);
        }
        #event-table th {
            background-color: #2c3e50;
            color: white;
            text-align: left;
            padding: 12px 15px;
            text-transform: uppercase;
            letter-spacing: 0.03em;
        }

        #event-table td {
            padding: 12px 15px;
            border-bottom: 1px solid #edf2f7;
            color: #4a5568;
        }
        #event-table tr:nth-child(even) {
            background-color: #f8fafc;
        }
        #event-table tr:hover {
            background-color: #f1f5f9;
        }
        #event-table a {
            color: #3182ce;
            text-decoration: none;
            font-weight: 600;
        }
        .footer {
            font-size: 12px;
            color: #a0aec0;
            margin-top: 20px;
        }
    </style>
    """
    
    # Create the full body by combining style + table
    #full_body = f"<html><head>{style}</head><body>{html_table}</body></html>"
    # Define your GitHub Pages URL once at the top of your script for easy editing later
    PUBLIC_TRACKER_URL = "https://skvarnaj.github.io/event-web-scraper/"

    full_body = f"""
    <html>
        <head>{style}</head>
        <body>
            <div class="email-container">
                <div class="table-header">
                    Here is the latest schedule from 
                    <a href="{PUBLIC_TRACKER_URL}" style="color: #007bff; text-decoration: underline; font-weight: bold;">tracked orgs</a> <3
                </div>
                {html_table}
                <p style="font-size: 11px; color: #999; margin-top: 20px;">
                    This report was automatically generated on {pd.Timestamp.now().strftime('%B %d, %Y')}
                </p>
            </div>
        </body>
    </html>
    """

    # Attach as 'html' — if you use 'plain', the CSS is ignored
    msg.attach(MIMEText(full_body, 'html'))

    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(SENDER_EMAIL, EMAIL_PASSWORD)
            server.send_message(msg)
        print("Aesthetic email sent successfully!")
    except Exception as e:
        print(f"Error sending email: {e}")

async def main():
    scraper = CraftScraper()
    results = await scraper.run_all()
    
    if not results:
        print("No events found.")
        return

    # 1. Load into DataFrame
    df = pd.DataFrame(results)

    # 2. Create the Hyperlink
    df['Organization'] = df.apply(
        lambda x: f'<a href="{x["URL"]}">{x["Organization"]}</a>', 
        axis=1
    )
    df = df.drop(columns=['URL'])

    # 3. Convert to Datetime for filtering and sorting
    # We use errors='coerce' to handle any "TBD" or "Check Website" entries safely
    df['temp_date'] = pd.to_datetime(df['Date'], format='mixed', errors='coerce')
    
    # --- DATE FILTERING LOGIC ---
    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    four_months_from_now = today + pd.DateOffset(months=4)
    
    # Filter: Keep events between today and 4 months from now
    # NOTE: not keeping events with not date (| (df['temp_date'].isna()))
    df = df[(df['temp_date'] >= today) & (df['temp_date'] <= four_months_from_now)]
    
    # 4. Sort by Date and Time
    df['Time'] = df['Time'].astype(str).str.lower().str.replace(r'(\d+)\s+(am|pm)', r'\1\2', regex=True)
    df['temp_time'] = pd.to_datetime(df['Time'].replace('all day', '12:00am'), format='%I:%M%p', errors='coerce').dt.time
    df = df.sort_values(by=['temp_date', 'temp_time'], ascending=True, na_position='last')

    # 5. Format the Date string with a period after the day (e.g., Sat. Jan 24, 2026)
    # We use .strftime to get the parts, then string replace the first comma
    df['Date'] = df['temp_date'].dt.strftime('%a, %b %d, %Y')
    df['Date'] = df['Date'].str.replace(',', '', n=1) # Replace only the FIRST comma
    df['Date'] = df['Date'].fillna('Check Website')

    # Cleanup temporary columns
    df = df.drop(columns=['temp_date', 'temp_time'])

    # 6. Send Email
    await send_email(df)

if __name__ == "__main__":
    asyncio.run(main())