import pika
import json
import os
from dotenv import load_dotenv
import requests
import sqlite3

# 1. Load environment variables
load_dotenv()
API_KEY = os.getenv("PPLX_API_KEY")
if not API_KEY:
    raise ValueError("Missing PPLX_API_KEY in .env file")

# 2. Perplexity analysis function (same as before)
def analyze_with_perplexity(text):
    url = "https://api.perplexity.ai/chat/completions"
    payload = {
        "model": "sonar",
        "messages": [
            {
                "role": "system",
                "content": (
                    "Analyze the sentiment and key themes in the user's message. "
                    "Output in this format:\n"
                    "Sentiment: <sentiment>\nThemes: <comma-separated themes>"
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

    lines = content.split("\n")
    sentiment = "Unknown"
    themes = []

    for line in lines:
        if line.startswith("Sentiment:"):
            sentiment = line.split(":", 1)[1].strip()
        if line.startswith("Themes:"):
            themes = [theme.strip() for theme in line.split(":", 1)[1].split(",")]

    return {"sentiment": sentiment, "themes": themes}


# 3. Setup SQLite DB
DB_FILE = "sentiment.db"

# Initialize DB if it doesn't exist
def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("""
    CREATE TABLE IF NOT EXISTS messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        content TEXT NOT NULL,
        sentiment TEXT NOT NULL,
        themes TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)
    conn.commit()
    conn.close()

def store_in_sqlite(message, sentiment, themes):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("""
        INSERT INTO messages (content, sentiment, themes)
        VALUES (?, ?, ?)
    """, (message, sentiment, json.dumps(themes)))
    conn.commit()
    conn.close()
    print(f"✅ Stored in SQLite: {message[:50]}...")

# 4. Process RabbitMQ messages
def process_message(ch, method, properties, body):
    message = body.decode('utf-8')
    print(f"📩 Received: {message}")

    try:
        result = analyze_with_perplexity(message)
        sentiment = result.get("sentiment", "Unknown")
        themes = result.get("themes", [])

        print(f"✅ Sentiment: {sentiment}")
        print(f"✅ Themes: {themes}")

        store_in_sqlite(message, sentiment, themes)
    except Exception as e:
        print(f"❌ Error processing message: {e}")

# 5. Consume from RabbitMQ
def consume_from_rabbitmq():
    init_db()
    connection = pika.BlockingConnection(pika.ConnectionParameters('localhost'))
    channel = connection.channel()
    channel.queue_declare(queue='news')
    channel.basic_consume(queue='news', on_message_callback=process_message, auto_ack=True)
    print("🚀 Waiting for messages...")
    channel.start_consuming()

if __name__ == "__main__":
    consume_from_rabbitmq()
