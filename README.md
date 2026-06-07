# WHMCS Webscraping

# Set Up
1. Clone this repository
2. Make sure you have Selenium and Python installed
3. Update credentials.txt with your WHMCS username and password (username on the first line, password on the second)

## Usage
Run the webscrape_WHMCS.py file to scrape subdomain and application data.
The webscraped info is stored in the applications.csv and subdomains.csv files.
The id of the last domain scraped is stored in last_domain.txt. This allows the script to resume at the next domain when it is next run. If you want to start over, you can run "python3 webscrape_WHMCS.py reset."