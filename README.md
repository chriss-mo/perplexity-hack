# World Sentimapper: Real-Time World News Sentiment Analysis Dashboard
For SDx Perplexity Hack Day  
[Live Link](https://chriss-mo-perplexity-hack-app-uadoc9.streamlit.app/)

## Overview
This project is a real-time world news sentiment analysis dashboard that processes articles from the New York Times RSS feed, analyzing their sentiment and geographical relevance. The goal is to provide insights into global financial news trends and visualize them interactively on a map.

## How It Works

### Data Ingestion
- **RabbitMQ** is used to create a message queue system that ingests real-time articles from the NYT RSS feed.
- The producer extracts key metadata (**title, summary, published date, and `nyt_geo` tags** for location) and sends it to the queue.

### Data Processing
- A **Python consumer** listens to the RabbitMQ queue and processes each article.
- Geographical information is extracted using `nyt_geo` tags and matched to countries using the **`pycountry`** library.
- If a valid country is found, the article content is analyzed using the **Perplexity Sonar API** to determine:
  - **Sentiment** → Positive, Negative, or Neutral
  - **Themes** → Key topics discussed in the article

### Storage
- The processed data is stored in a **SQLite database** for efficient querying and retrieval.

### Visualization
- A **Streamlit dashboard** queries the SQLite database and displays the articles in a table.
- **Pydeck** is used to plot the articles on a world map, with colors representing sentiment:
  - 🟢 **Green** = Positive
  - 🔴 **Red** = Negative
  - 🟡 **Yellow** = Neutral
- To prevent clustering, **coordinate jittering** is applied to make overlapping markers more distinguishable.

## Tech Stack
- ✅ **RabbitMQ** – Message queue for real-time data ingestion
- ✅ **SQLite** – Lightweight database for local storage
- ✅ **Perplexity Sonar API** – Sentiment and theme extraction from text
- ✅ **Pycountry** – Country matching and validation
- ✅ **Streamlit** – Interactive dashboard
- ✅ **Pydeck** – Map-based visualization with colored markers
- ✅ **Feedparser** – RSS feed parsing

## Features
- ✔️ Real-time sentiment analysis of financial news
- ✔️ Interactive geographical mapping of articles
- ✔️ Clean and standardized sentiment parsing
- ✔️ Dynamic marker placement with jittering for visibility

## Usage Instructions

### Prerequisites
Ensure you have the following installed:
- **Python 3.x**
- **RabbitMQ server** running
- Required Python packages (install using `requirements.txt`)

### Setup
1. **Clone the repository:**
   ```sh
   git clone https://github.com/your-repo/financial-news-sentiment.git
   cd financial-news-sentiment
   ```
3. **Start RabbitMQ (if not already running):**
   ```sh
   rabbitmq-server
   ```
4. **Run the producer to ingest articles:**
   ```sh
   python rss_producer.py
   ```
5. **Run the consumer to process articles:**
   ```sh
   python rss_consumer.py
   ```
6. **Launch the Streamlit dashboard:**
   ```sh
   streamlit run app.py
   ```

### Expected Output
- A real-time stream of financial news articles with sentiment analysis.
- An interactive map displaying articles color-coded by sentiment.
- A table listing articles with metadata, themes, and sentiment scores.

## Contribution
Feel free to contribute by submitting issues or pull requests. Any enhancements to visualization, sentiment analysis accuracy, or database optimization are welcome!

## License
This project is licensed under the **MIT License**.

---
This project demonstrates a complete end-to-end data pipeline – from ingestion and processing to storage and visualization – combining modern messaging systems, machine learning APIs, and real-time interactive dashboards.


