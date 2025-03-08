import streamlit as st
import os
import json
import sqlite3
from dotenv import load_dotenv

# Load environment variables (if you need anything else, or just for consistency)
load_dotenv()

DB_FILE = "sentiment.db"  # Adjust if your DB file is in another location

def get_data():
    """
    Connects to SQLite, fetches the rows in messages table,
    and returns a list of dicts like:
    [{'content': ..., 'sentiment': ..., 'themes': ..., 'created_at': ...}, ...]
    """
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    # Fetch rows from messages table
    cursor.execute("SELECT content, sentiment, themes, created_at FROM messages ORDER BY id DESC")
    rows = cursor.fetchall()
    conn.close()

    data = []
    for row in rows:
        content = row[0]
        sentiment = row[1]
        # 'themes' is stored as a JSON string, so parse it
        themes = json.loads(row[2])
        created_at = row[3]

        data.append({
            'content': content,
            'sentiment': sentiment,
            'themes': themes,
            'created_at': created_at
        })
    return data

# Streamlit Dashboard
st.title("📈 Financial News Sentiment Dashboard (SQLite)")

records = get_data()
if not records:
    st.write("No data available yet. Waiting for new messages...")
else:
    for item in records:
        st.write(f"**Content**: {item['content']}")
        st.write(f"Sentiment: {item['sentiment']}")
        st.write(f"Themes: {', '.join(item['themes'])}")
        st.write(f"Timestamp: {item['created_at']}")
        st.write("---")
