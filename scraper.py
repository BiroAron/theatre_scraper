import requests
from bs4 import BeautifulSoup as bs
from datetime import datetime
import pandas as pd
import json
import re
import os
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import NoSuchElementException

class TheaterPlay:
    def __init__(self):
        self.day_name = ''
        self.date = ''
        self.time = ''
        self.available_seats = ''
        self.playwright = ''
        self.title = ''
        self.director = ''
        self.progcomment = ''
        self.location = ''
        self.details = []

    def __str__(self):
        return f'{self.day_name} - {self.date} - {self.time} - {self.available_seats} - {self.playwright} - {self.title} - {self.director} - {self.progcomment} - {self.location} - {self.details}'

url = 'https://www.huntheater.ro/musor/program/'
result = requests.get(url)
doc = bs(result.text, 'html.parser')

months = []
for option in doc.select('select.dateselect option'):
    value = option.get('value')
    if value.startswith(str(datetime.now().year)):
        months.append(value)

all_plays = []

for month in months:
    url = 'https://www.huntheater.ro/musor/program/?ym=' + month + '&p=0'
    result = requests.get(url)
    doc = bs(result.text, 'html.parser')

    plays_raw = doc.find_all(class_=re.compile(r'programrow prg-(?!.*szurke).*'))

    for el in plays_raw:
        play = TheaterPlay()
        play.day_name = el.find('div', class_='prgcaldayname').text
        play.date = month + '-' + el.find('div', class_='pcaldate').text
        play.time = el.find('div', class_='pcaltime').text
        play.playwright = el.find('div', class_='proghilite').text
        play.progcomment = el.find('div', class_='progcomment').text

        play.location = play.progcomment.split('-')[0].strip()

        progtitle_div = el.find('div', class_='progtitle')
        play.title = progtitle_div.find('h1').text

        link = 'https://www.huntheater.ro' + progtitle_div.find('a').get('href')

        specific_play_result = requests.get(str(link))
        doc_specific_play = bs(specific_play_result.text, 'html.parser')

        date_div = doc_specific_play.find('div', class_='perfbottom')

        if date_div:
            hrefs = date_div.find_all('a')
            for link in hrefs:
                if play.date in link.get('href'):
                    url = link.get('href')
                    options = webdriver.ChromeOptions()
                    options.add_argument('-headless')
                    driver = webdriver.Chrome(options=options)
                    driver.get(url)
                    time.sleep(4)
                    try:
                        auditorium_price_categories = driver.find_element(By.ID, 'auditorium-price-categories')
                        seats = 0
                        for p in auditorium_price_categories.find_elements(By.TAG_NAME, 'p'):
                            text = p.text.strip()
                            numbers = re.findall(r'\b\d+\b', text)
                            seats += int(numbers[2])
                        play.available_seats = str(seats)
                    except NoSuchElementException:
                        element_exists = len(driver.find_elements(By.CSS_SELECTOR, "span.zold")) > 0
                        if element_exists:
                            play.available_seats = "Elerhető jegyek"
                        else:
                            try:
                                div = driver.find_element(By.ID, 'viewmode')
                                text = div.text.strip()
                                play.available_seats = text
                            except:
                                play.available_seats = "Elfogyott"
                    driver.quit()

        bottom_left = el.find('div', class_='programrow-bottomleft')
        if bottom_left:
            play.director = bottom_left.find('span').next_sibling
        for h6_element in el.find_all('h6'):
            play.details.append(h6_element.text)
        all_plays.append(play)

current_date = datetime.now().strftime("%Y-%m-%d")

json_file_path = 'plays.json'
write_mode = 'a' if os.path.exists(json_file_path) else 'w'
with open(json_file_path, write_mode) as file:
    for play in all_plays:
        play_dict = play.__dict__
        play_dict['scraping_date'] = current_date
        play_dict['location'] = play.location
        play_json = json.dumps(play_dict)
        file.write(play_json + '\n')

excel_file_path = 'theater_plays_kolozsvar.xlsx'
df = pd.DataFrame([play.__dict__ for play in all_plays])
if os.path.exists(excel_file_path):
    df_existing = pd.read_excel(excel_file_path)
    df = pd.concat([df_existing, df], ignore_index=True)
df.to_excel(excel_file_path, index=False)
