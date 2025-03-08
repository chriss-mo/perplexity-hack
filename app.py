import streamlit as st
from influxdb_client import InfluxDBClient
import json
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Load InfluxDB config from environment variables
INFLUX_URL = os.getenv("INFLUX_URL", "http://localhost:8086")
INFLUX_TOKEN = os.getenv("INFLUX_TOKEN")
INFLUX_ORG = os.getenv("INFLUX_ORG")
INFLUX_BUCKET = os.getenv("INFLUX_BUCKET", "financial_news")

if not all([INFLUX_URL, INFLUX_TOKEN, INFLUX_ORG, INFLUX_BUCKET]):
    raise ValueError("Missing InfluxDB configuration in .env file")

# Connect to InfluxDB
client = InfluxDBClient(url=INFLUX_URL, token=INFLUX_TOKEN, org=INFLUX_ORG)

def get_data():
    query = f'from(bucket: "{INFLUX_BUCKET}") |> range(start: -1h)'
    tables = client.query_api().query(query)
    data = []
    for table in tables:
        for row in table.records:
            data.append({
                'title': row['title'],
                'sentiment': row['sentiment'],
                'themes': json.loads(row['themes'])
            })
    return data

# Streamlit Dashboard
st.title("📈 Financial News Sentiment Dashboard")

data = get_data()
if not data:
    st.write("No data available yet. Waiting for new messages...")

for item in data:
    st.write(f"**{item['title']}**")
    st.write(f"Sentiment: {item['sentiment']}")
    st.write(f"Themes: {', '.join(item['themes'])}")
    st.write("---")
