import time
import datetime
import re
import pandas as pd
import random
import numpy as np
import scipy as sci
from os.path import exists
import sys
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select
from selenium.common.exceptions import NoSuchElementException
from bs4 import BeautifulSoup
from selenium.webdriver.firefox.options import Options as FirefoxOptions
from selenium import webdriver

def extract_ndcs(raw_ndc):
    groups = (
                re.findall(
                    "(?P<Labeler>\d{3,5})-?(?P<Product>\d{3,4})-?(?P<Package>\d{1,2})",
                    raw_ndc
                )
            )
    result = []
    if len(groups) == 0:
        return result
    
    for group in groups:
        labeler, product, package = group
        fda_ndc = labeler + "-" + product + "-" + package
        if len(labeler) < 5:
            labeler = "0" + labeler
        if len(product) < 4:
            product = "0" + product
        if len(package) < 2:
            package = "0" + package
        result.append({'fda_ndc': fda_ndc, 'hipaa_ndc': labeler + product + package})

    return result


def simplify_reason(_reason):
    reason = _reason.lower()
    if re.search('demand', reason) is not None and re.search('increase',reason) is not None:
        return "Increased demand"
    if re.search('shortage', reason) is not None and re.search('ingredient',reason) is not None:
        return "Ingredient shortage"
    if re.search('discontinu', reason) is not None and re.search('manufactu',reason) is not None:
        return "Discontinued manufacturing"
    if re.search('delay', reason) is not None or re.search('good manufactu',reason) is not None:
        if re.search('shipping',reason) is not None:
            return "Shipping delay"
        return "Manufacturing delay"
    return "Other"

options = FirefoxOptions()
options.add_argument("--headless")
driver = webdriver.Firefox(options=options)

# Initialize
events = pd.DataFrame()
drug_names, links, statuses = [], [], []
base_link = "https://www.accessdata.fda.gov/scripts/drugshortages/"
driver.get(base_link + "default.cfm")

# Pull down all rows of the overview table 
records = Select(driver.find_element("xpath","/html/body/div[2]/div/main/article/div/div/div[3]/div/div[1]/div/div[1]/label/select"))
records.select_by_value('-1')
soup = BeautifulSoup(driver.page_source,'html.parser')
table = soup.find("table",{"id": "cont"})
rows = table.find_all('tr')

# for each row in the overview table, extract the name, status, and link of each shortage event 
for row in rows:
    detail_links = row.find_all('a', href=True)
    if len(detail_links) > 0:
        drug_name = detail_links[0].get_text()
        link = detail_links[0].get('href')
        status_raw = row.find_all('td')[1]
        status = status_raw.get_text().strip()
        statuses.append(status)
        drug_names.append(drug_name)
        links.append(link)

# create the overview df for processing events
over_df = pd.DataFrame(
    zip(drug_names, links, statuses), 
    columns = ['drug_name', 'link', 'status']
    )
drug_events_master = pd.DataFrame

for _index, drug_event in over_df.iterrows():
#for drug_event in [over_df.iloc[1]]:
    time.sleep(random.random() * 2)
    # Go to the drug event's page 
    print("Creating events for",drug_event['drug_name'])
    detail_link = base_link + drug_event['link']
    driver.get(detail_link)
    html = driver.page_source
    soup = BeautifulSoup(html,'html.parser')

    # Look for the pharma manufacturers and event information sections
    # There will be as many info sections as pharma manufacturers, so we can use an index enumerator 
    pharmas = soup.find_all('h3', {'class':"background_text accordion-header ui-accordion-header ui-helper-reset ui-state-default ui-accordion-icons ui-corner-all"})
    infos = soup.find_all('div', {'class': 'ui-accordion-content ui-helper-reset ui-widget-content ui-corner-bottom'})
    pharma_master = pd.DataFrame()
    status_master = pd.DataFrame()
    event_status, event_reason, event_availability, event_info = None, None, None, None

    for i in range(len(infos)):
        # Get the pharma manufacturer info and contact info 
        contact_email, contact_phone = None, None
        pharma_groups = re.search('(.*)\((\w*)\s*(\d{1,2}\/\d{1,2}\/\d{4})',pharmas[i].get_text().strip())
        pharma_name = pharma_groups[1].strip()
        # The contact info of a pharma mfg will be within the pharma mfg's container 
        _contact_raw = (infos[i].find('div').get_text().strip().split("\n"))
        if len(_contact_raw) > 1:
            (infos[i].find('div').get_text().strip().split("\n"))
            # Parsing numbers isn't critical, the contact phone only needs to be human readable
            contact_methods = _contact_raw
            for method in contact_methods:
                if re.match("\d",method) is not None:
                    contact_phone = method.strip()
                if re.match("@",method) is not None:
                    contact_email = method.strip()

        # Pull the most relevant information from the little blurb above the tables 
        event_information = soup.find('p',{'style': 'margin-left:15px;'})
        event_status, event_start, event_end, event_category = None, None, None, None
        duration_matcher = re.compile("(?P<start_month>\d\d)/(?P<start_day>\d\d)/(?P<start_year>\d{4})(\s?-\s?(?P<end_month>\d\d)/(?P<end_day>\d\d)/(?P<end_year>\d{4}))?")
        for bit in event_information.children:
            # You have to crawl each child because the website uses different classes if it's a duration or single date
            _key = bit.get_text().strip() 
            _sib = bit.next_sibling
            if _sib is not None:
                # As long as we're not out of children
                while len(_sib.get_text()) <= 1:
                    # Keep scanning siblings until we find one that isn't a newline or space or other detritus 
                    _sib = _sib.next_sibling
                sib = _sib.get_text().strip()
                # From here on, it's a case statement with regex 
                if re.search("Status",_key) is not None:
                    event_status = sib
                elif re.search("Duration",_key) is not None:
                    date_groups = re.match(duration_matcher,sib)
                    event_start = date_groups['start_year'] + "-" + date_groups['start_month'] + "-" + date_groups['start_day']
                    event_end = date_groups['end_year'] + "-" + date_groups['end_month'] + "-" + date_groups['end_day']
                elif re.search("Date first",_key) is not None:
                    event_start = sib
                elif re.search("Therapeutic",_key) is not None:
                    event_category = sib

        # tries to find a table of information 
        # Sometimes the FDA lists shortages in an unordered list. Sometimes it's a table. :shrug:
        info_table = infos[i].find('table',{'class':'table-bordered table-striped footable'})
        if info_table is None: 
            for header in infos[i].find_all('strong'):
                if re.match("Presentation",header.get_text().strip()) is not None:
                    extracted_ndcs = extract_ndcs(header.findNext().get_text().strip())
                if re.match("Note",header.get_text().strip()) is not None:
                    event_status = header.findNext().get_text().strip()
        else:
                headers = [header.get_text() for header in info_table.find_all('th')]
                info_table_rows = info_table.find_all('tr')
                status_company = [pharma_name for _ in range(len(info_table_rows))]
                for row in range(len(info_table_rows)):
                    if row > 0: # skip the header row\n",
                        row_fields = info_table_rows[row].find_all('td')
                        extracted_ndcs = extract_ndcs(row_fields[0].get_text().strip())
                        event_availability = (row_fields[1].get_text().strip())
                        event_info = (row_fields[2].get_text().strip())
                        event_reason = (row_fields[3].get_text().strip())

        for _ndc in extracted_ndcs:
            event = {
                'drug_name': drug_event.drug_name,
                'drug_ndc_fda': _ndc['fda_ndc'],
                'drug_ndc_hipaa': _ndc['hipaa_ndc'],
                'manufacturer_name': pharma_name,
                'manufacturer_contact_phone': contact_phone,
                'manufacturer_contact_email': contact_email,
                'event_start_date': event_start,
                'event_end_date': event_end,
                'event_status': event_status,
                'reason': event_reason,
                'availability': event_availability,
                'info_1': event_info,
                'info_2': event_status,
                'url': detail_link
            }

            #and concat with the master events df
            events = pd.concat([events,pd.DataFrame([event])])
            print(f"I have created a new event for {event['drug_name']} ({event['drug_ndc_fda']} by {event['manufacturer_name']}).")

            event_status, event_reason, event_availibilty, event_info = None, None, None, None


events['simple_reason'] = events['reason'].fillna('Unknown').apply(lambda r : simplify_reason(r))

month = datetime.datetime.now().month
day = datetime.datetime.now().day
year = datetime.datetime.now().year
suffix = str(year) + "_" + str(month) + "_" + str(day) + "_"
events.reset_index(drop=True).to_csv(suffix+'events.csv')   