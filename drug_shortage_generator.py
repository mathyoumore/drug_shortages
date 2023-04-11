import pandas as pd
import datetime
import re 
import urllib.request
from time import sleep
import os


def extract_ndcs(raw_ndc: str) -> list:
    """Generate an array of hashes of NDCs.
    Returns an FDA and HIPAA version of the NDC in an array for iterating over.
    Returns an empty array if it finds nothing.
    :param str raw_ndc: The string that you think contains NDC(s) 
    :rtype list
    """
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
        result.append({'ndc_fda': fda_ndc, 'ndc_hipaa': labeler + product + package})

    return result

presentation_matcher = re.compile("(?P<Presentation>[^(]*)\s\((?P<NDCs>(.*))\)?$",re.M)
reverse_presentation_matcher = re.compile("NDCs?\s(?P<NDCs>[\d-]*)\s*\((?P<Presentation>.*)\)")
ndc_matcher = re.compile("(?P<Labeler>\d{3,5})-?(?P<Product>\d{3,4})-?(?P<Package>\d{1,2})")

url = 'https://www.accessdata.fda.gov/scripts/drugshortages/Drugshortages.cfm'
month = datetime.datetime.now().month
day = datetime.datetime.now().day
year = datetime.datetime.now().year
prefix = str(year) + "_" + str(month) + "_" + str(day) + "_"
filename = prefix + "drugshortages_raw.csv"

print("The website is down somewhat regularly. If this fails or times out, please be patient and try again in half an hour or so. Remember to support policies that fund open and reliable data!")

urllib.request.urlretrieve(url, filename)
df = pd.read_csv(filename)
os.remove(filename)

print("CSV received, processing")

converted_hashes = []
for _index, row in df.iterrows():
    converted_hash = {}
    # Copy the contents of every row except the ' Presentation' column
    for k,v in enumerate(row.items()):
        if v[0] != ' Presentation':
            # Clean up the keys while we're here
            # Comes in like " Generic Name", goes out like "generic_name"
            clean_key = v[0].strip().lower().replace(' ','_')
            converted_hash[clean_key] = v[1]
        else: 
            # Once we've found the presentation k:v pair, use them to extract NDCs and Presentations
            untreated_presentation = v[1]
            extracted_ndcs = extract_ndcs(v[1])
            target_no_ndc = re.sub(ndc_matcher,"",v[1],0)
            presentation = re.sub("\(.*\)$","",target_no_ndc)

    for e_ndc in extracted_ndcs:
        if len(e_ndc) > 0:
            # if the extractor was successful, expect a hash like {ndc_fda: '...', ndc_hipaa: '...'}
            ndc_hash = converted_hash | {'presentation': presentation.strip(),'ndc_fda': e_ndc['ndc_fda'], 'ndc_hipaa': e_ndc['ndc_hipaa']}
        else:
            # otherwise just pass in the exact contents that we got from the csv download
            # this is needed to guard against GIGO
            ndc_hash = converted_hash | {'presentation': untreated_presentation.strip(),'ndc_fda': None, 'ndc_hipaa': None}
        converted_hashes.append(ndc_hash)

month = datetime.datetime.now().month
day = datetime.datetime.now().day
year = datetime.datetime.now().year
prefix = "shortages/" + str(year) + "_" + str(month) + "_" + str(day) + "_"

target_holding = "shortages"
if not os.path.exists(target_holding):
    os.makedirs(target_holding)

pd.DataFrame(converted_hashes).to_csv(prefix + 'drug_shortages.csv')
print("All done! Check it out at",prefix + 'drug_shortages.csv')