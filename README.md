# drug_shortages
Quick way to generate a list of all drugs that are experiencing (or have experienced) shortages in the US
Generated from available data on the [FDA Access Data website](https://www.accessdata.fda.gov/scripts/drugshortages/default.cfm)
by Matthew Mohr

## How to use 
Clone repo (or just copy the file) and run the "drug_shortage_generayor.py" script. Once successful, it will create a folder called "Shortages" and put a date-prefixed output .csv file of its findings. This is different from the "Download Current Drug Shortages" link on the Access Data website because this will create a row for every NDC it finds and provide the FDA and HIPAA versions of those NDCs. **Requires Python 3 or higher as well as Pandas 1.5 or higher.**

If, for whatever reason, the FDA removes the "Download Current Drug Shortages" link, a data miner script is also available at "drugshortagespider.py." This script requires Selenium, Firefox, and the relevant drivers as well as BeautifulSoup. This script should only be used if the "Download Current Drug Shortages" button is removed from the Access Data website. If the link still exists, just moved, let me know. 

## Usage recommendations 
This script can be run as often as you'd like (within reason), but will not change very much day-to-day. I would recommend running it once a week or so or as-needed for your analyses. 
