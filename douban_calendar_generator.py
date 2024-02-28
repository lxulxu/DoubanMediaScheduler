# -*- coding: gbk -*-
import json
import os
import re
import time
from datetime import datetime, timedelta

import feedparser
import requests
from bs4 import BeautifulSoup
from icalendar import Calendar, Event

rss_url = os.environ.get("RSS_URL")

def  read_movie_data(file_path)                    : 
    try: 
        with open(file_path, 'r', encoding='utf-8') as file: 
            data = file.read()
            if not data:
                return []
            return json.loads(data)
    except json.JSONDecodeError:
        return []
    except FileNotFoundError:
        return []

def write_movie_data(file_path, data):
    with open(file_path, 'w') as file:
        json.dump(data, file, indent=4)

def update_movie_data(rss_movies, existing_movies): 
    current_date = datetime.now()
    one_year_later = current_date + timedelta(days=365)
    
    for movie in rss_movies: 
        if current_date <= datetime.strptime(movie['release_date'], "%Y-%m-%d") <= one_year_later:
            if movie not in existing_movies:
                existing_movies.append(movie)
    return existing_movies

def get_movies_from_rss(rss_url):
    feed = feedparser.parse(rss_url)
    movies = []

    for entry in feed.entries: 
        if '想看' in entry.title:
            cleaned_title = entry.title.replace('想看', '').strip()
            with open('log.txt', 'a') as f: 
                f.write(cleaned_title)
            movie_info = {
                'title': cleaned_title,
                'link': entry.link
            }
            movies.append(movie_info)
    
    return movies

def fetch_release_date(url): 
    time.sleep(30)
    try: 
        header = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) '
                      'Chrome/70.0.3538.102 Safari/537.36 Edge/18.18363'}
        response = requests.get(url=url, headers=header)
        if response.status_code == 200:
           soup = BeautifulSoup(response.content, 'html.parser')
           release_date = soup.find('span', {'property': 'v:initialReleaseDate'}).get_text()
           return extract_valid_date(release_date)

    except Exception as e: 
        return None

def extract_valid_date(date_str): 
    match = re.search(r'\d{4}-\d{2}-\d{2}', date_str)
    if match:
        return match.group(0)
    return None

def get_release_date(movie, existing_movies)                                      : 
    for existing_movie in existing_movies                                             : 
        if  existing_movie['title'] == movie['title'] and 'release_date' in existing_movie: 
                return existing_movie['release_date']
    return fetch_release_date(movie['link'])

def create_ics(movies, filename='movies_calendar.ics'):
    cal = Calendar()
    cal.add('prodid', '-//My Movie Calendar//mxm.dk//')
    cal.add('version', '2.0')

    for movie in movies: 
        event = Event()
        event.add('summary', movie['title'])
        event.add('dtstart', datetime.strptime(movie['release_date'], "%Y-%m-%d"))
        event.add('dtend', datetime.strptime(movie['release_date'], "%Y-%m-%d")) 
        event.add('url', movie['link'])
        cal.add_component(event)

    with open(filename, 'wb') as f:
        f.write(cal.to_ical())

    return filename

if __name__  == "__main__":
    file_path = 'movies_data.json'
    existing_movies = read_movie_data(file_path)

    movies = get_movies_from_rss(rss_url)
    temp_movies_data = []

    for movie in movies:
        release_date = get_release_date(movie, existing_movies)
        if release_date:
            temp_movies_data.append({'title': movie['title'], 'link': movie['link'], 'release_date': release_date})

    updated_movies = update_movie_data(temp_movies_data, existing_movies)
    write_movie_data(file_path, updated_movies)   

    ics_file = create_ics(updated_movies)