'''
Author: lxulxu
Date: 2024-03-01 15:21:33
LastEditors: lxulxu
LastEditTime: 2024-03-06 13:43:20
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

def fetch_movie_details(url): 
    try: 
        time.sleep(random.uniform(1, 3))
        headers               = {"User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko)"}
        response              = requests.get(url, headers=headers)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')

        name_element = soup.find('span', {'property': 'v:itemreviewed'})
        movie_name   = name_element.get_text()if name_element else "Unknown Movie"

        date_element = soup.find('span', {'property': 'v:initialReleaseDate'})
        release_date = None
        if date_element: 
            date_string = date_element.get_text()
            match = re.search(r'\d{4}-\d{2}-\d{2}', date_string)
            if match: 
                release_date = match.group(0)

        return movie_name, release_date
    except Exception as e:
        logging.error(f"Error fetching release date for {url}: {e}")
        return "Unknown Movie", None
    
def fetch_rss_feed(rss_url):
    try:
        return feedparser.parse(rss_url)
    except Exception as e:
        logging.error(f"Error fetching RSS feed: {e}")
        return None

def fetch_and_update_movies(rss_url, cache_file='movies_data.json', max_attempts=10): 
    try:
        if os.path.exists(cache_file):
            with open(cache_file, 'r', encoding='utf-8') as file:
                data = json.load(file)
        else:
            data = {}

        feed = fetch_rss_feed(rss_url)
        if not feed:
            logging.error("Failed to fetch or parse the RSS feed.")
            return
        for entry in feed.entries: 
            if  "想看" in entry.title: 
                movie_link   = entry.link
                if movie_link not in data: 
                    movie_name, release_date       = fetch_movie_details(movie_link)
                    data[movie_link]['name'] = movie_name
                    if release_date:
                        data[movie_link]['release_date'] = release_date

        no_date_movies = [link for link, info in data.items() if not info.get('release_date')]
        for movie_link in random.sample(no_date_movies, min(len(no_date_movies), max_attempts)):
            movie_name, release_date       = fetch_movie_details(movie_link)
            data[movie_link]['name'] = movie_name
            if release_date:
                data[movie_link]['release_date'] = release_date

        with open(cache_file, 'w', encoding='utf-8') as file:
            json.dump(data, file, ensure_ascii=False, indent=4)

    except Exception as e:
        logging.error(f"Error fetching and updating movies: {e}")

def generate_ics_file(cache_file='movies_data.json', ics_path="movies.ics"): 
    calendar = Calendar()
    today    = datetime.date.today()
    three_months_ago = today - datetime.timedelta(days=90)
    one_year_later = today + datetime.timedelta(days=365)
    try                                            : 
        if   os.path.exists(cache_file)                     : 
            with open(cache_file, 'r', encoding='utf-8') as file: 
                data = json.load(file)

            for info in data.values():
                release_date = info.get('release_date')
                if release_date: 
                    release_date_dt = datetime.datetime.strptime(release_date, "%Y-%m-%d").date()
                    if three_months_ago <= release_date_dt <= one_year_later:
                        event = Event()
                        event.name = info.get('name')
                        event.begin = datetime.datetime.combine(release_date_dt, datetime.time(23, 0))
                        calendar.events.add(event)


        with open(ics_path, 'w', encoding="utf-8") as f: 
            f.write(calendar.serialize())

    except Exception as e:
        logging.error(f"Error generating ICS file: {e}")

if __name__ == "__main__":
    rss_url = os.environ.get("RSS_URL")
    fetch_and_update_movies(rss_url=rss_url)
    generate_ics_file()