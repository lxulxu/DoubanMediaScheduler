'''
Author: lxulxu
Date: 2024-03-01 15:21:33
LastEditors: lxulxu
LastEditTime: 2024-03-01 18:56:33
Description: 

Copyright (c) 2024 by lxulxu, All Rights Reserved. 
'''
import datetime
import json
import logging
import os
import random
import re
import time

import feedparser
import requests
from bs4 import BeautifulSoup
from ics import Calendar, Event

logging.basicConfig(filename='movie_scraper.log', level=logging.INFO, format='%(asctime)s %(levelname)s:%(message)s')

def fetch_rss_feed(rss_url):
    try:
        return feedparser.parse(rss_url)
    except Exception as e:
        logging.error(f"Error fetching RSS feed: {e}")
        return None

def save_movie_info(movie_name, movie_link, release_date, cache_file='movies_data.json', max_no_date_entries=10): 
    try:
        if not os.path.exists(cache_file) or os.stat(cache_file).st_size == 0:
            with open(cache_file, 'w', encoding='utf-8') as file:
                json.dump({}, file, ensure_ascii=False, indent=4)

        with open(cache_file, 'r', encoding='utf-8') as file:
            data = json.load(file)

        if release_date: 
            data[movie_link] = {'name': movie_name, 'release_date': release_date}
        else:
            no_date_entries = sum(1 for info in data.values() if 'release_date' not in info)
            if no_date_entries < max_no_date_entries:
                data[movie_link] = {'name': movie_name}

        with open(cache_file, 'w', encoding='utf-8') as file:
            json.dump(data, file, ensure_ascii=False, indent=4)

    except json.JSONDecodeError: 
        logging.error(f"JSON format error in {cache_file}. Initializing file.")
        with open(cache_file, 'w', encoding='utf-8') as file:
            json.dump({movie_name: {'link': movie_link, 'release_date': release_date}}, file, ensure_ascii=False, indent=4)
    except Exception as e:
        logging.error(f"Error saving movie info for {movie_name}: {e}")


def extract_valid_date(date_str): 
    match = re.search(r'\d{4}-\d{2}-\d{2}', date_str)
    if match:
        return match.group(0)
    return None

def fetch_release_date(url, cache_file='movie_data.json'): 
    try:
        if os.path.exists(cache_file):
            with open(cache_file, 'r', encoding='utf-8') as file:
                data = json.load(file)
                for movie, info in data.items():
                    if info['link'] == url:
                        return info['release_date']
    except Exception as e:
        logging.error(f"Error reading from cache: {e}")

    headers = {'User-Agent': 'Mozilla/5.0'}
    try:
        time.sleep(random.uniform(1, 3))
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        date_string = soup.find('span', {'property': 'v:initialReleaseDate'}).get_text()
        return extract_valid_date(date_string)
    except Exception as e:
        logging.error(f"Error fetching release date for {url}: {e}")
        return None
    
def get_movies_from_rss(): 
    rss_url = os.environ.get("RSS_URL")
    feed = fetch_rss_feed(rss_url)
    if not feed:
        logging.error("Failed to fetch or parse the RSS feed.")
        return
    for entry in feed.entries:
        if "想看" in entry.title:
            movie_name = entry.title.replace('想看', '').strip()
            movie_link = entry.link
            release_date = fetch_release_date(movie_link)
            if release_date:
                save_movie_info(movie_name, movie_link, release_date)

def generate_ics_file(cache_file='movies_data.json', ics_path="movies.ics"): 
    calendar = Calendar()
    today = datetime.date.today()
    one_year_later = today + datetime.timedelta(days=365)
    try                                            : 
        if os.path.exists(cache_file)                     : 
            with open(cache_file, 'r', encoding='utf-8') as file: 
                data = json.load(file)
                for movie_link, info in data.items(): 
                    release_date = info.get('release_date')
                    if not release_date: 
                        release_date = fetch_release_date(movie_link)
                        if release_date:
                            info['release_date'] = release_date
                            with open(cache_file, 'w', encoding='utf-8') as file:
                                json.dump(data, file, ensure_ascii=False, indent=4)

                    if release_date and today <= datetime.datetime.strptime(release_date, "%Y-%m-%d").date() <= one_year_later:
                        event = Event()
                        event.name = info['name']
                        event.begin = release_date
                        calendar.events.add(event)

        with open(ics_path, 'w', encoding="utf-8") as f:
            f.write(calendar.serialize())

    except Exception as e:
        logging.error(f"Error generating ICS file: {e}")

if __name__ == "__main__":
    get_movies_from_rss()
    generate_ics_file()