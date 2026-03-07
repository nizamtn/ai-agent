from flask import Flask, request, render_template, jsonify
from newsapi import NewsApiClient
from geopy.geocoders import Nominatim
import os
import threading
import time

app = Flask(__name__)

# NewsAPI Configuration
NEWS_API_KEY = "53bae5a8652b456085fb6cf57ad07d58"
newsapi = NewsApiClient(api_key=NEWS_API_KEY)

# Geopy Configuration
geolocator = Nominatim(user_agent="village_ai")

# Global data stores
news_alerts = [
    "Flood warning issued in Kerala district",
    "Power outage reported due to storm",
    "Road collapse reported after heavy rain(result)"
]
complaints = []
heatmap_data = []

# Global status counters
road = 0
water = 0
garbage = 0
light = 0

def fetch_news_async():
    """Background task to fetch news without blocking Flask."""
    global news_alerts
    while True:
        try:
            print("Fetching news alerts in background...")
            articles = newsapi.get_everything(
                q="flood OR water shortage OR road accident OR power outage OR garbage",
                language="en",
                sort_by="publishedAt",
                page_size=5
            )

            if articles and "articles" in articles:
                new_alerts = []
                for article in articles["articles"]:
                    title = article.get("title")
                    if title and any(word in title.lower() for word in ["flood","water","road","power","garbage"]):
                        new_alerts.append(title)
                
                if new_alerts:
                    news_alerts = new_alerts
                    print(f"Updated news_alerts: {len(news_alerts)} items.")
            
        except Exception as e:
            print(f"Error fetching news in background: {e}")
        
        # Refresh every 10 minutes
        time.sleep(600)

# Start background news thread
news_thread = threading.Thread(target=fetch_news_async, daemon=True)
news_thread.start()

@app.route("/", methods=["GET", "POST"])
def home():
    global road, water, garbage, light, news_alerts, heatmap_data

    recommendation = ""
    
    if request.method == "POST":
        # Using .get() for safer access
        complaint_text = request.form.get("complaint", "").strip()
        lat = request.form.get("lat")
        lon = request.form.get("lon")
        place = request.form.get("place", "").strip()

        location_name = "Unknown Location"

        # Geocoding logic
        if place:
            try:
                location = geolocator.geocode(place)
                if location:
                    lat = str(location.latitude)
                    lon = str(location.longitude)
                    heatmap_data.append([location.latitude, location.longitude, 1])
                    location_name = place
            except Exception as e:
                print(f"Geocoding error: {e}")

        # Fallback to reverse geocoding if lat/lon provided manually
        if lat and lon and lat != "" and lon != "" and location_name == "Unknown Location":
            try:
                rev_loc = geolocator.reverse(f"{lat}, {lon}")
                if rev_loc:
                    location_name = rev_loc.address.split(',')[0]
                heatmap_data.append([float(lat), float(lon), 1])
            except Exception as e:
                print(f"Reverse geocoding error: {e}")

        if complaint_text:
            # Add enriched data to complaints
            complaints.append({
                "text": complaint_text,
                "location": location_name,
                "timestamp": time.strftime("%H:%M")
            })

            # Classify grievance
            t_low = complaint_text.lower()
            if any(k in t_low for k in ["road", "pothole", "street", "highway"]):
                road += 1
            elif any(k in t_low for k in ["water", "leak", "pipe", "tap", "well"]):
                water += 1
            elif any(k in t_low for k in ["garbage", "waste", "trash", "sanitation", "smell"]):
                garbage += 1
            elif any(k in t_low for k in ["light", "dark", "electric", "power", "grid"]):
                light += 1

    # Intelligent Recommendation Logic
    counts = {
        "Road Infrastructure": road,
        "Water Supply": water,
        "Waste Management": garbage,
        "Electrical Grid": light
    }

    if sum(counts.values()) == 0:
        recommendation = "All systems reporting normal operations."
    else:
        top_focus = max(counts, key=counts.get)
        recommendation = f"Predictive AI Alert: {top_focus} requires immediate logistical priority."

    return render_template(
        "ai.html",
        complaints=complaints,
        road=road,
        water=water,
        garbage=garbage,
        light=light,
        recommendation=recommendation,
        heatmap_data=heatmap_data,
        news_alerts=news_alerts
    )

if __name__ == "__main__":
    app.run(debug=True, port=5000, host="0.0.0.0")
