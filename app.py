import streamlit as st
import pandas as pd
import sqlite3
import json
import random
import pydeck as pdk

country_coords = json.load(open("country.json"))

# 2. Jitter function to spread out points in the same country
def jitter_coords(lat, lon, offset=2.0):  # Increased offset for more spread
    """
    offset in degrees; larger offset = more spread.
    For large countries, you can use a bigger offset.
    """
    lat += random.uniform(-offset, offset)
    lon += random.uniform(-offset, offset)
    return lat, lon

# 3. Define colors for sentiments
sentiment_colors = {
    "Positive": [0, 200, 0, 160],   # green
    "Neutral": [200, 200, 0, 160],  # yellow
    "Negative": [200, 0, 0, 160],   # red
    "Unknown": [128, 128, 128, 160] # gray default
}

def get_data():
    conn = sqlite3.connect("sentiment.db")
    cursor = conn.cursor()
    cursor.execute("""
        SELECT content, country, sentiment, themes, created_at
        FROM messages
        ORDER BY id DESC
    """)
    rows = cursor.fetchall()
    conn.close()

    data = []
    for row in rows:
        content, country, sentiment, themes_json, created_at = row
        themes = json.loads(themes_json)

        if country in country_coords:
            lat = country_coords[country]["lat"]
            lon = country_coords[country]["lon"]

            # Jitter each article's coordinates so multiple articles
            # in the same country won't perfectly overlap
            lat_jittered, lon_jittered = jitter_coords(lat, lon)

            data.append({
                "content": content,
                "country": country,
                "sentiment": sentiment,
                "themes": themes,
                "created_at": created_at,
                "lat": lat_jittered,
                "lon": lon_jittered
            })
    return data

# 4. Main Streamlit code
data = get_data()
if not data:
    st.write("No data available yet. Waiting for new messages...")
else:
    df = pd.DataFrame(data)
    st.title("🌍 News Sentiment and Geographical Dashboard")

    # Display data in a table
    st.write("### Latest Articles")
    st.dataframe(df[["content", "country", "sentiment", "themes", "created_at"]])

    # Create a column for marker colors based on sentiment
    def get_color(sentiment):
        return sentiment_colors.get(sentiment, [128, 128, 128, 160])  # default gray if not found

    df["color"] = df["sentiment"].apply(get_color)

    # 5. Build a ScatterplotLayer in Pydeck
    layer = pdk.Layer(
        "ScatterplotLayer",
        data=df,
        get_position='[lon, lat]',
        get_color='color',
        get_radius=150000,  # Adjust radius based on zoom level
        pickable=True,
    )

    # 6. Set the viewport / initial camera position
    view_state = pdk.ViewState(
        latitude=df["lat"].mean() if not df.empty else 20,
        longitude=df["lon"].mean() if not df.empty else 0,
        zoom=1,
        pitch=0,
    )

    tooltip = {
        "html": "<b>Country:</b> {country} <br/><b>Sentiment:</b> {sentiment}",
        "style": {
            "backgroundColor": "steelblue",
            "color": "white"
        }
    }

    # 7. Render the map using Pydeck
    r = pdk.Deck(
        layers=[layer],
        initial_view_state=view_state,
        tooltip=tooltip
    )
    st.pydeck_chart(r)

    # 8. Sidebar to show article titles when a country is clicked
    if "selected_country" not in st.session_state:
        st.session_state.selected_country = None

    if st.session_state.selected_country:
        st.sidebar.title(f"Articles from {st.session_state.selected_country}")
        country_articles = df[df["country"] == st.session_state.selected_country]
        for _, row in country_articles.iterrows():
            st.sidebar.write(f"- {row['content']}")

    # 9. Add a callback to update the selected country
    def update_selected_country(info):
        st.session_state.selected_country = info["object"]["country"]

    # Update the selected country based on click events
    if st.session_state.selected_country:
        st.sidebar.title(f"Articles from {st.session_state.selected_country}")
        country_articles = df[df["country"] == st.session_state.selected_country]
        for _, row in country_articles.iterrows():
            st.sidebar.write(f"- {row['content']}")

    # 10. Right sidebar for search functionality
    st.sidebar.title("Search Articles")
    search_query = st.sidebar.text_input("Search for anything in the database")

    if search_query:
        search_results = df[df.apply(lambda row: search_query.lower() in row.to_string().lower(), axis=1)]
        st.sidebar.write(f"### Search Results for '{search_query}'")
        for _, row in search_results.iterrows():
            st.sidebar.write(f"- {row['content']}")
