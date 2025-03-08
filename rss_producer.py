import pika
import feedparser
import time

# NYT RSS feed URL
RSS_FEED_URL = "https://rss.nytimes.com/services/xml/rss/nyt/Business.xml"

def get_rss_items():
    feed = feedparser.parse(RSS_FEED_URL)
    for entry in feed.entries:
        yield {
            'title': entry.title,
            'link': entry.link,
            'summary': entry.summary,
            'published': entry.published
        }

def publish_to_rabbitmq():
    connection = pika.BlockingConnection(pika.ConnectionParameters('localhost'))
    channel = connection.channel()
    channel.queue_declare(queue='news')

    while True:
        print("Fetching RSS feed...")
        for item in get_rss_items():
            message = f"{item['title']} - {item['summary']}"
            channel.basic_publish(exchange='',
                                  routing_key='news',
                                  body=message)
            print(f"Published: {message}")

        time.sleep(30)  # Fetch new items every 30 seconds

if __name__ == "__main__":
    publish_to_rabbitmq()
