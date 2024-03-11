
import datetime
import json
import logging
import os
import random
import re
import time
from datetime import timedelta

import feedparser
import pytz
import requests
from bs4 import BeautifulSoup
from ics import Calendar, Event

logging.basicConfig(filename='media_scraper.log', level=logging.INFO, format='%(asctime)s %(levelname)s:%(message)s')
session = requests.Session()
session.headers.update({"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko)"})

def fetch_html_content(url, sleep_interval=(1, 3)):
    try:
        time.sleep(random.uniform(*sleep_interval))
        response = session.get(url)
        response.raise_for_status()
        return BeautifulSoup(response.text, 'html.parser')
    except Exception as e:
        logging.error(f"Unexpected error for URL {url}: {str(e)}")
        return None
    
def fetch_media_details(url):
    soup = fetch_html_content(url)
    if not soup:
        return "Unknown Media", None
    
    patterns = {
        "subject": {
            "name": ('span', {'property': 'v:itemreviewed'}),
            "date": ('span', {'property': 'v:initialReleaseDate'})
        },
        "game": {
            "name": ('title', {}),
            "date": ('dt', lambda x: x and '\u9884\u8ba1\u4e0a\u5e02\u65f6\u95f4:' in x, 'dd')
        }
    }

    for media_type, pattern in patterns.items():
        if media_type in url:
            name_element = soup.find(*pattern["name"][:-1], **pattern["name"][-1])
            media_name = name_element.get_text().strip() if name_element else "Unknown Media"

            if isinstance(pattern["date"], tuple) and len(pattern["date"]) == 3:
                date_dt_element = soup.find(pattern["date"][0], string=pattern["date"][1])
                date_element = date_dt_element.find_next_sibling(pattern["date"][2]) if date_dt_element else None
            else:
                date_element = soup.find(*pattern["date"])

            release_date = parse_date_from_element(date_element)
            return media_name, release_date

    return "Unknown Media", None

def parse_date_from_element(element):
    if element:
        date_string = element.get_text()
        match = re.search(r'\d{4}-\d{2}-\d{2}', date_string)
        if match:
            return match.group(0)
    return None

def fetch_rss_feed(rss_url):
    try:
        return feedparser.parse(rss_url)
    except Exception as e:
        logging.error(f"Error fetching RSS feed: {e}")
        return None     

def update_media_data(entry, data):
    media_link = entry['link']
    if media_link not in data:
        media_name, release_date = fetch_media_details(media_link)
        data[media_link] = {'name': media_name, 'release_date': release_date}

def fetch_and_update_media(rss_url, cache_file='media_data.json', max_attempts=10): 
    data = load_data(cache_file)
    
    feed = fetch_rss_feed(rss_url)
    if feed and feed.entries:
        for entry in feed.entries:
            if "\u60f3\u770b" in entry.title or "\u60f3\u73a9" in entry.title:
                update_media_data(entry, data)

        no_date_media = [link for link, info in data.items()]
        for media_link in random.sample(no_date_media, min(len(no_date_media), max_attempts)):
            update_media_data({'link': media_link}, data)

    save_data(data, cache_file)
    return data

def load_data(cache_file):
    if os.path.exists(cache_file):
        with open(cache_file, 'r', encoding='utf-8') as file:
            return json.load(file)
    return {}

def save_data(data, cache_file):
    with open(cache_file, 'w', encoding='utf-8') as file:
        json.dump(data, file, ensure_ascii=False, indent=4)

def generate_ics_file(data, ics_path="media.ics"): 
    calendar = Calendar()
    tz = pytz.timezone('Asia/Shanghai')

    now = datetime.datetime.now(tz)
    start_range = now - timedelta(days=90)
    end_range = now + timedelta(days=180)

    for info in data.values():
        release_date = info.get('release_date')
        if release_date: 
            date = datetime.datetime.strptime(release_date, "%Y-%m-%d")
            date_with_timezone = tz.localize(date)
            if start_range <= date_with_timezone <= end_range:
                event = Event()
                event.name = info.get('name')
                event.begin = date_with_timezone.replace(hour=23, minute=0)
                calendar.events.add(event)

        with open(ics_path, 'w', encoding="utf-8") as f: 
            f.write(calendar.serialize())


if __name__ == "__main__":
    rss_url = os.environ.get("RSS_URL")
    if rss_url is None:
        logging.error("RSS_URL environment variable is not set.")

    data = fetch_and_update_media(rss_url=rss_url)
    generate_ics_file(data)