import pika
import json
import os
import re
from dotenv import load_dotenv
import requests
import sqlite3
import pycountry  # for validating country names

# 1. Load environment variables
load_dotenv()
API_KEY = os.getenv("PPLX_API_KEY")
if not API_KEY:
    raise ValueError("Missing PPLX_API_KEY in .env file")

# 2. Extract country from message text using the "nyt_geo:" keyword
def extract_country(text):
    # Look for <category domain="http://www.nytimes.com/namespaces/keywords/nyt_geo">CountryName</category>
    match = re.search(r'<category\s+domain="http://www\.nytimes\.com/namespaces/keywords/nyt_geo">([^<]+)</category>', text)
    if match:
        country_candidate = match.group(1).strip()
        try:
            country = pycountry.countries.lookup(country_candidate)
            return country.name  # Standardized country name
        except LookupError:
            return None
    return None

# 3. Setup SQLite DB (with an additional column for country)
DB_FILE = "sentiment.db"

def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("""
    CREATE TABLE IF NOT EXISTS messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        content TEXT NOT NULL,
        country TEXT,
        sentiment TEXT NOT NULL,
        themes TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)
    conn.commit()
    conn.close()

def store_in_sqlite(message, country, sentiment, themes):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("""
        INSERT INTO messages (content, country, sentiment, themes)
        VALUES (?, ?, ?, ?)
    """, (message, country, sentiment, json.dumps(themes)))
    conn.commit()
    conn.close()
    print(f"✅ Stored in SQLite with country {country}: {message[:50]}...")

# 4. Perplexity analysis function (for sentiment and themes)
def analyze_with_perplexity(text):
    url = "https://api.perplexity.ai/chat/completions"
    payload = {
        "model": "sonar",
        "messages": [
            {
                "role": "system",
                "content": (
                    "Analyze the sentiment of the following article and output in the format:\n"
                    "Sentiment: <Positive/Negative/Neutral>\nThemes: <comma-separated themes>"
                )
            },
            {"role": "user", "content": text}
        ],
        "max_tokens": 123,
        "temperature": 0.2,
        "top_p": 0.9,
        "search_domain_filter": None,
        "return_images": False,
        "return_related_questions": False,
        "top_k": 0,
        "stream": False,
        "presence_penalty": 0,
        "frequency_penalty": 1,
        "response_format": None
    }
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }

    response = requests.post(url, json=payload, headers=headers)
    if response.status_code != 200:
        raise Exception(f"Request to Perplexity API failed: {response.status_code} - {response.text}")

    data = response.json()
    content = data["choices"][0]["message"]["content"]

    sentiment = "Unknown"
    themes = []
    for line in content.split("\n"):
        if line.startswith("Sentiment:"):
            sentiment = line.split(":", 1)[1].strip()
        elif line.startswith("Themes:"):
            themes = [t.strip() for t in line.split(":", 1)[1].split(",")]
    return {"sentiment": sentiment, "themes": themes}

# 5. Process each RabbitMQ message
def process_message(ch, method, properties, body):
    message = body.decode("utf-8")
    print(f"📩 Received: {message[:50]}...")

    # Extract country info from the message
    country = extract_country(message)
    if not country:
        print("Skipping message because no valid country was found.")
        return

    try:
        result = analyze_with_perplexity(message)
        sentiment = result.get("sentiment", "Unknown")
        themes = result.get("themes", [])

        print(f"✅ Sentiment: {sentiment}, Themes: {themes}, Country: {country}")
        store_in_sqlite(message, country, sentiment, themes)
    except Exception as e:
        print(f"❌ Error processing message: {e}")

# 6. Consume from RabbitMQ
def consume_from_rabbitmq():
    init_db()
    connection = pika.BlockingConnection(pika.ConnectionParameters("localhost"))
    channel = connection.channel()
    channel.queue_declare(queue="news")
    channel.basic_consume(queue="news", on_message_callback=process_message, auto_ack=True)
    print("🚀 Waiting for messages...")
    channel.start_consuming()

if __name__ == "__main__":
    consume_from_rabbitmq()
