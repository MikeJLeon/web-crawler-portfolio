# -*- coding: utf-8 -*-
"""
Created on 01/27/2019
NSC - AD440 CLOUD PRACTICIUM
@author: Michael Leon

Changed ownership on 02/09/2019
@author: Dao Nguyen
Last edited by Dao Nguyen 02/19/2019

"""

import urllib.request
import re
import os
import json
import time
import uuid
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
import selenium.webdriver.chrome.service as service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from bs4 import BeautifulSoup
import time
from dateutil.parser import parse
from datetime import datetime
import os
from pymongo import MongoClient
# pprint library is used to make the output look more pretty
from pprint import pprint
# connect to MongoDB, change the << MONGODB URL >> to reflect your own connection string

client = MongoClient(os.environ['MONGO_DB_KEY'])
db = client.events
# Issue the serverStatus command and print the results
serverStatusResult=db.command("serverStatus")
collection = db.OFA
collection.remove({})
FOUND_LIST = []
QUEUE = []
OUTPUT = {}
DATA = {}
SOUP = []
OFA = "https://outdoorsforall.org/events-news/calendar/"
GOOGLE_CHROME_BIN = os.environ['GOOGLE_CHROME_SHIM']


def ofa_crawl(url):
    global QUEUE
    global FOUND_LIST
    global SOUP
    chrome_options = webdriver.ChromeOptions()
    chrome_options.binary_location = GOOGLE_CHROME_BIN
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--no-sandbox')
    #driver = webdriver.Chrome(executable_path="C:\\Users\\micha\\Documents\\GitHub\\web-crawler-portfolio\\chromedriver", chrome_options=chrome_options)
    driver = webdriver.Chrome(executable_path="chromedriver", chrome_options=chrome_options)
    pages = 1

    # Grab all links on calendar for 3 months from current month
    print("Starting OFA Crawler; " + str(datetime.now()))
    driver.get(url)
    while pages <= 3:
        jsQueue = []
        if pages == 1:
            try:
                print("\nConnecting to " + url + "; success\n")
            except:
                print("\nConnecting to " + url + "; failed\n")
                break

        # set selenium to click to the next month from current calendar month
        if pages == 2:
            count = 0
            while(count != 10):
                try:
                    driver.get((By.XPATH, '//*[@id="main_cal"]/tbody/tr/td/table/tbody/tr[1]/td[3]')).click()
                    print("page 2")
                except:
                    print("Page had issue clicking next, retrying")
                    count += 1
                    if(count == 10):
                        print("Selenium failed to click next")
                        break

        # set selenium to click to the month after next month
        elif pages == 3:
             while(count != 10):
                try:
                    driver.get((By.XPATH, '//*[@id="main_cal"]/tbody/tr/td/table/tbody/tr[1]/td[3]')).click()
                    print("page 3")
                except:
                    print("Page had issue clicking next, retrying")
                    count += 1
                    if(count == 10):
                        print("Selenium failed to click next")
                        break

        # parse the pages and add all links found to a list
        soup = BeautifulSoup(driver.page_source, "html.parser")
        for row in soup.find_all("div"):
            if row.get("onclick"):
                jsQueue.append(row.get("class")[0])
                break
        try:
            x = driver.find_elements_by_class_name(jsQueue[0])
        except:
            pass

        # to refresh the elements and retrieve them on the current page
        if pages >= 2:
            time.sleep(0.45)
            count = 0
            while count != 5:
                soup = BeautifulSoup(driver.page_source, "html.parser")
                for row in soup.find_all("div"):
                    if row.get("onclick"):
                        jsQueue.append(row.get("class")[0])
                try:
                    x = driver.find_elements_by_class_name(jsQueue[0])
                except:
                    pass
                count += 1

        # Click all found elements to open page and grab the URL
        for row in x:
            count = 0
            while(count != 10):
                try:
                    row.click()
                    driver.switch_to.window(driver.window_handles[1])
                    break
                except:
                    count += 1
                    if(count != 10):
                        print("Couldnt click event, retrying...")

            # check for links that previously found from the previous month, if not found
            # add to list
            if driver.current_url not in FOUND_LIST:

                FOUND_LIST.append(driver.current_url)

                current_url = driver.current_url
                current_soup = BeautifulSoup(driver.page_source, "html.parser")
                for linebreak in current_soup.find_all('br'):
                    linebreak.extract()
                # Calls OFAScraper module to populate a dictionary object to add to the output
                data = open_link(current_soup, current_url)
                print(data)
                collection.insert_one(data)
                driver.switch_to.window(driver.window_handles[0])

            else:
                driver.switch_to.window(driver.window_handles[0])

        pages += 1
    driver.quit()

# This open work on the data from each link, call for helpers to get additional data
# return data and status


def open_link(current_soup, current_url):
    data = {}
    print("Found event " + current_url)
    data["ID"] = str(uuid.uuid5(uuid.NAMESPACE_DNS, current_url))
    data["URL"] = current_url
    data["Title"] = str(find_title(current_soup))
    data["Description"] = str(find_description(current_soup))
    data["Date"] = str(find_date(current_soup))
    data["Location"] = str(find_location(current_soup))
    return data

# This function to get the title of each event from link


def find_title(soup):
    if soup.find(class_="header-theme"):
        title = soup.find(class_="header-theme").text
        title = title.replace('\n', '')
        title = title.replace('\t', '')
        return title


# This function to get the description of each event from link
def find_description(soup):
    desc = soup.find("span", attrs={"class": "event-desc-theme"})
    p_desc = ""
    loc = ""
    time = ""
    # Look for all p elements to find description, ignore location and attempt to find time.
    for row in desc.findAll("p"):
        try:
            if "Export:" not in row.text:
                if "location" in row.text.lower():
                    pass
                else:
                    p_desc = p_desc + row.text
                if ("pm" in row.text.lower() or "am" in row.text.lower()) and any(c.isdigit() for c in row.text):
                    time += row.text + " "
        except:
            pass
    if not p_desc:
        p_desc = "None"
    return(p_desc)

# This function to get the date from each event from link


def find_date(soup):
    for row in soup.findAll(attrs={"class": "subheader-theme"}):
        row = row.text.splitlines()
        try:
            for val in row:
                try:
                    if parse(val):
                        return(str(parse(val).date()))
                except:
                    pass
        except:
            pass
    return("Unknown")

# This function to get the location of each event from link


def find_location(soup):
    desc = soup.find("span", attrs={"class": "event-desc-theme"})
    loc = ""
    for row in desc.findAll(text=True, recursive=False):
        if(len(row) > 1):
            loc = re.sub("\r\n", "", row)
    if len(loc) > 0:
        return(loc.replace('\n', '').replace('\t', ''))
    else:
        return("Unknown")
    # print(OUTPUT)W

# Main function


def main():
    count = 0
    while count != 5:
        try:
            ofa_crawl(OFA)
            break
        except Exception as e:
            print("Error gathering URL data, " + str(e))
            count += 1
            print("Retrying selenium...")
    print("\nClosing OFA Crawler; " + str(datetime.now()))


main()
