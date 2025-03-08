import pika
from perplexity import Perplexity
import json
import os
from dotenv import load_dotenv
from influxdb_client import InfluxDBClient, Point, WriteOptions

# Load environment variables from .env file
load_dotenv()

# Initialize Perplexity Sonar API
API_KEY = os.getenv("SONAR_API_KEY")
if not API_KEY:
    raise ValueError("Missing SONAR_API_KEY in .env file")

sonar = Perplexity(api_key=API_KEY)

# Setup InfluxDB connection
INFLUX_URL = os.getenv("INFLUX_URL", "http://localhost:8086")
INFLUX_TOKEN = os.getenv("INFLUX_TOKEN")
INFLUX_ORG = os.getenv("INFLUX_ORG")
INFLUX_BUCKET = os.getenv("INFLUX_BUCKET", "financial_news")

if not all([INFLUX_URL, INFLUX_TOKEN, INFLUX_ORG]):
    raise ValueError("Missing InfluxDB configuration in .env file")

client = InfluxDBClient(url=INFLUX_URL, token=INFLUX_TOKEN, org=INFLUX_ORG)
write_api = client.write_api(write_options=WriteOptions(batch_size=1))

# Store results in InfluxDB
def store_in_influxdb(title, sentiment, themes):
    point = Point("news") \
        .tag("title", title) \
        .field("sentiment", sentiment) \
        .field("themes", json.dumps(themes))
    write_api.write(bucket=INFLUX_BUCKET, record=point)
    print(f"✅ Stored in InfluxDB: {title[:50]}...")

# Process RabbitMQ message
def process_message(ch, method, properties, body):
    message = body.decode('utf-8')
    print(f"📩 Received: {message}")

    try:
        # Use Sonar API to extract sentiment and themes
        response = sonar.analyze(message)
        sentiment = response.get("sentiment", "Unknown")
        themes = response.get("themes", [])

        print(f"✅ Sentiment: {sentiment}")
        print(f"✅ Themes: {themes}")

        # Store in InfluxDB
        store_in_influxdb(message, sentiment, themes)

    except Exception as e:
        print(f"❌ Error processing message: {e}")

# Consume RabbitMQ messages
def consume_from_rabbitmq():
    connection = pika.BlockingConnection(pika.ConnectionParameters('localhost'))
    channel = connection.channel()
    channel.queue_declare(queue='news')

    channel.basic_consume(queue='news',
                          on_message_callback=process_message,
                          auto_ack=True)

    print("🚀 Waiting for messages...")
    channel.start_consuming()

if __name__ == "__main__":
    consume_from_rabbitmq()
