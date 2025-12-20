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
# TO DO: hide password
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
            max-width: 800px;
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
    full_body = f"""
    <html>
        <head>{style}</head>
        <body>
            <div class="email-container">
                <div class="table-header">Here is the latest schedule from tracked orgs <3</div>
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
    # We combine 'Organization' and 'URL' into a new HTML string
    df['Organization'] = df.apply(
        lambda x: f'<a href="{x["URL"]}">{x["Organization"]}</a>', 
        axis=1
    )

    # 3. Remove the URL column now that it's embedded
    df = df.drop(columns=['URL'])

    # 4. Sort by Date
    df['temp_date'] = pd.to_datetime(df['Date'], format='mixed', errors='coerce')
    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    df = df[(df['temp_date'] >= today) | (df['temp_date'].isna())]
    df = df.sort_values(by='temp_date', ascending=True, na_position='last')
    df = df.drop(columns=['temp_date'])
    df['Date'] = pd.to_datetime(df['Date'], format='mixed', errors='coerce').dt.strftime('%a, %b %d, %Y')
    df['Date'] = df['Date'].fillna('Check Website')

    # 5. Send Email (Make sure to use escape=False in the send_email function!)
    await send_email(df)

if __name__ == "__main__":
    asyncio.run(main())