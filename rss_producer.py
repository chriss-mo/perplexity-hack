import pika
import feedparser
import json
import time

# NYT RSS feed URL
RSS_FEED_URL = "https://rss.nytimes.com/services/xml/rss/nyt/Business.xml"

def get_rss_items():
    feed = feedparser.parse(RSS_FEED_URL)
    for entry in feed.entries:
        # Extract countries from 'nyt_geo' category if present
        countries = []
        if hasattr(entry, 'tags'):
            for tag in entry.tags:
                # feedparser may store the domain in 'scheme' or 'term'
                # Typically:
                #   tag.scheme -> "http://www.nytimes.com/namespaces/keywords/nyt_geo"
                #   tag.term -> "Afghanistan"
                if hasattr(tag, 'scheme') and tag.scheme and 'nyt_geo' in tag.scheme.lower():
                    countries.append(tag.term)


        # Build the data we want to send
        item_data = {
            'title': entry.title,
            'link': entry.link,
            'summary': entry.summary,
            'published': getattr(entry, 'published', ''),
            'countries': countries
        }
        yield item_data

def publish_to_rabbitmq():
    connection = pika.BlockingConnection(pika.ConnectionParameters('localhost'))
    channel = connection.channel()
    channel.queue_declare(queue='news')

    while True:
        print("Fetching RSS feed...")
        for item in get_rss_items():
            # Convert our item dictionary to JSON
            message_json = json.dumps(item)
            channel.basic_publish(
                exchange='',
                routing_key='news',
                body=message_json.encode('utf-8')
            )
            print(f"Published: {item['title'][:50]}... with {len(item['countries'])} countries")
        time.sleep(30)  # Fetch new items every 30 seconds

if __name__ == "__main__":
    publish_to_rabbitmq()
