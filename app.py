import streamlit as st
import pandas as pd
import sqlite3
import json

# A simple mapping of some country names to coordinates
country_coords = {
    "United States": {"lat": 37.0902, "lon": -95.7129},
    "Canada": {"lat": 56.1304, "lon": -106.3468},
    "United Kingdom": {"lat": 55.3781, "lon": -3.4360},
    "France": {"lat": 46.2276, "lon": 2.2137},
    "Germany": {"lat": 51.1657, "lon": 10.4515},
    # Add more countries as needed...
}

# Define colors for sentiments
sentiment_colors = {
    "Positive": [0, 200, 0, 160],  # green
    "Neutral": [200, 200, 0, 160],   # yellow
    "Negative": [200, 0, 0, 160]     # red
}

def get_data():
    conn = sqlite3.connect("sentiment.db")
    cursor = conn.cursor()
    cursor.execute("SELECT content, country, sentiment, themes, created_at FROM messages ORDER BY id DESC")
    rows = cursor.fetchall()
    conn.close()

    data = []
    for row in rows:
        content, country, sentiment, themes_json, created_at = row
        themes = json.loads(themes_json)
        if country in country_coords:
            lat = country_coords[country]["lat"]
            lon = country_coords[country]["lon"]
            data.append({
                "content": content,
                "country": country,
                "sentiment": sentiment,
                "themes": themes,
                "created_at": created_at,
                "lat": lat,
                "lon": lon
            })
    return data

# Load data from SQLite
data = get_data()
if not data:
    st.write("No data available yet. Waiting for new messages...")
else:
    df = pd.DataFrame(data)

    st.title("🌍 News Sentiment and Geographical Dashboard")

    # Display data in a table
    st.write("### Latest Articles", df[["content", "country", "sentiment", "themes", "created_at"]])

    # Using Pydeck for a custom map with colored markers based on sentiment
    import pydeck as pdk

    # Create a column for marker colors based on sentiment
    def get_color(sentiment):
        return sentiment_colors.get(sentiment, [128, 128, 128, 160])  # default gray

    df["color"] = df["sentiment"].apply(get_color)

    # Define a ScatterplotLayer
    layer = pdk.Layer(
        "ScatterplotLayer",
        data=df,
        get_position='[lon, lat]',
        get_color="color",
        get_radius=50000,  # adjust radius as needed
        pickable=True,
    )

    # Set the viewport location
    view_state = pdk.ViewState(
        latitude=df["lat"].mean() if not df.empty else 20,
        longitude=df["lon"].mean() if not df.empty else 0,
        zoom=1,
        pitch=0,
    )

    # Render the map using Pydeck
    st.pydeck_chart(pdk.Deck(layers=[layer], initial_view_state=view_state, tooltip={"text": "Country: {country}\nSentiment: {sentiment}"}))
