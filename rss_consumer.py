import pika
import json
import os
import re
from dotenv import load_dotenv
import requests
import sqlite3
import pycountry

# 1. Load environment variables
load_dotenv()
API_KEY = os.getenv("PPLX_API_KEY")
if not API_KEY:
    raise ValueError("Missing PPLX_API_KEY in .env file")

# 2. Setup SQLite DB (with an additional column for country)
DB_FILE = "sentiment.db"

def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("""
    CREATE TABLE IF NOT EXISTS messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        content TEXT NOT NULL,    -- We'll store the combined article text (title+summary) here
        country TEXT,
        sentiment TEXT NOT NULL,
        themes TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)
    conn.commit()
    conn.close()

def store_in_sqlite(article_text, country, sentiment, themes):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("""
        INSERT INTO messages (content, country, sentiment, themes)
        VALUES (?, ?, ?, ?)
    """, (article_text, country, sentiment, json.dumps(themes)))
    conn.commit()
    conn.close()
    print(f"✅ Stored in SQLite with country {country}: {article_text[:50]}...")


import re

def parse_sentiment_and_themes(response_text):
    """
    Takes Perplexity's raw response text and normalizes it, removing stray asterisks
    or partial words that might break the 'Sentiment:' parsing. Also attempts to clamp
    sentiment to 'Positive', 'Negative', or 'Neutral' (or 'Unknown').
    """

    # 1) Remove all asterisks in one go, just in case there's '**', '***', etc.
    cleaned_text = re.sub(r'\*+', '', response_text)

    # 2) Split into lines
    lines = cleaned_text.split("\n")
    sentiment = "Unknown"
    themes = []

    for line in lines:
        line = line.strip()
        if line.startswith("Sentiment:"):
            sentiment_raw = line.split(":", 1)[1].strip()
            sentiment = sentiment_raw
        elif line.startswith("Themes:"):
            themes_raw = line.split(":", 1)[1]
            themes = [t.strip() for t in themes_raw.split(",")]

    # 3) If we got something like "Unknown\nNegative", remove 'Unknown'
    sentiment = sentiment.replace("Unknown", "").strip()
    if not sentiment:
        sentiment = "Unknown"

    # 4) Lowercase and clamp to known categories if desired
    #    e.g. if you see "slightly negative" or "very negative", just treat as "Negative"
    sentiment_lower = sentiment.lower()
    if "positive" in sentiment_lower:
        sentiment = "Positive"
    elif "negative" in sentiment_lower:
        sentiment = "Negative"
    elif "neutral" in sentiment_lower:
        sentiment = "Neutral"
    else:
        sentiment = "Unknown"

    return sentiment, themes



# 3. Perplexity analysis function (for sentiment and themes)
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
    raw_text = data["choices"][0]["message"]["content"]

    # Use the new robust parser:
    sentiment, themes = parse_sentiment_and_themes(raw_text)
    return {"sentiment": sentiment, "themes": themes}


# 4. Process each RabbitMQ message
def process_message(ch, method, properties, body):
    # Decode the JSON payload that the producer sends
    message_str = body.decode("utf-8")
    data = json.loads(message_str)

    title = data.get("title", "")
    summary = data.get("summary", "")
    countries = data.get("countries", [])
    # Combine title and summary as the "text" we'll analyze
    article_text = f"{title}\n{summary}".strip()

    print(f"📩 Received: {title[:50]}... with {len(countries)} country candidates.")

    # Find a valid country
    valid_country = None
    for c in countries:
        # e.g. "St Louis (Mo)" -> remove parentheses
        c_clean = re.sub(r"\(.*?\)", "", c).strip()
        try:
            found_country = pycountry.countries.lookup(c_clean)
            valid_country = found_country.name  # standardize
            break
        except LookupError:
            # If c_clean isn't recognized, we ignore
            pass

    if not valid_country:
        print("Skipping article because no valid country was found.")
        return

    try:
        # Run sentiment analysis via Perplexity
        result = analyze_with_perplexity(article_text)
        sentiment = result.get("sentiment", "Unknown")
        themes = result.get("themes", [])

        print(f"✅ Sentiment: {sentiment}, Themes: {themes}, Country: {valid_country}")
        store_in_sqlite(article_text, valid_country, sentiment, themes)
    except Exception as e:
        print(f"❌ Error processing message: {e}")

# 5. Consume from RabbitMQ
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
