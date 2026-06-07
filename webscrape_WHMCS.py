import sys
from selenium.webdriver import Chrome
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions
from selenium.common.exceptions import StaleElementReferenceException, NoSuchElementException, TimeoutException

WAIT_TIME = 10
ERRORS_FILE = 'out/errors.txt'
APPLICATIONS_FILE = 'out/applications.csv'
DOMAINS_FILE = 'out/subdomains.csv'
LAST_DOMAIN_FILE = 'out/last_domain.txt'

def webscrape_cpanel(driver, applications_list, subdomains_list, username):
    apps_href = driver.find_element(By.ID, 'item_myapps').get_attribute('href')
    domains_href = driver.find_element(By.ID, 'item_domains').get_attribute('href')

    # Find apps and add to applications list
    driver.get(apps_href)

    num_apps = driver.find_element(By.ID, 'i_header_tab_installs_num').text
    if (num_apps == '0'):
        return []

    app_links = driver.find_elements(By.XPATH, "//div[contains(@class,'i_toolbar')]/a[.//div[contains(@class,'i_icon_edit')]]")

    app_urls = [link.get_attribute("href") for link in app_links]
    count = 0

    for href in app_urls:
        count += 1
        print(f"Processing app {count}/{len(app_urls)}")
        driver.get(href)

        try: 
            settings_button = WebDriverWait(driver, 10).until(
                expected_conditions.element_to_be_clickable((By.XPATH, "//a[contains(@href, '/settings') and normalize-space()='Settings']"))
            )
            settings_button.click()
        except TimeoutException:
            try:
                settings_button = WebDriverWait(driver, 10).until(
                    expected_conditions.element_to_be_clickable((By.XPATH, "//a[contains(@href, '/settings') and normalize-space()='Settings']"))
                )
                settings_button.click()
            except NoSuchElementException:
                print("Error in app " + str(count) + ": Could not find settings button")
            continue;

        # settings_button = driver.find_element(By.XPATH, "//a[contains(@href, '/settings') and normalize-space()='Settings']")
        # settings_button.click()
        
        driver.implicitly_wait(2)
        try:
            website_name = driver.find_element(By.ID, 'field_title').get_attribute('value')
        except:
            website_name = "Not Found"

        try:
            website_url = driver.find_element(By.ID, 'field_url').find_element(By.TAG_NAME, 'option').text
        except:
            website_url = "Not Found"

        try:
            application_button = driver.find_element(By.XPATH, "//a[.//div[normalize-space()='Application']]")
            application_button.click()
            
            admin_email = WebDriverWait(driver, 1).until(
                expected_conditions.presence_of_element_located((By.ID, "field_email"))
            ).get_attribute("value")
        except:
            admin_email = "Not Found"

        driver.implicitly_wait(WAIT_TIME)

        applications_list.append([website_name, website_url, admin_email])

    # Find subdomains and add to subdomains list
    driver.get(domains_href)

    try:
        main_domain_row = WebDriverWait(driver, 1).until(
            expected_conditions.presence_of_element_located((By.XPATH, "//tr[.//span[contains(text(), 'Main Domain')]]"))
        )
        main_domain_name = main_domain_row.find_element(By.CSS_SELECTOR, "a[id$='_domain_link']").get_attribute('href').removeprefix("https://").removeprefix("http://").rstrip("/")
    except:
        main_domain_name = "Not Found"

    domain_rows = driver.find_elements(By.CSS_SELECTOR, "td[id$='_domain']")

    for row in domain_rows:
        try:
            domain_name = row.find_element(By.CSS_SELECTOR, "a[id$='_domain_link']").get_attribute('href').removeprefix("https://").removeprefix("http://").rstrip("/")
        except NoSuchElementException:
            domain_name = "Not Found"
        except:
            domain_name = "Not Found"
        if (main_domain_name != domain_name):
            subdomains_list.append([main_domain_name, username, domain_name])


def init_driver():
    driver = Chrome()
    driver.get("https://sites.carleton.edu/manage/whmcs-admin/login.php?logout=1")
    driver.implicitly_wait(WAIT_TIME)
    return driver


def get_credentials():
    # Get the username and password
    try:
        user = open("credentials.txt", "r", encoding="UTF-8").readlines()
        username = user[0].strip('\n')
        password = user[1]
    except FileNotFoundError:
        username = input("Enter your username: ")
        password = input("Enter your password: ")
    return (username, password)


def login_to_WHMCS(driver, username, password):
    driver.find_element(By.NAME, 'username').send_keys(username)
    driver.find_element(By.NAME,'password').send_keys(password)
    driver.find_element(By.CSS_SELECTOR,'input[value=Login]').click()


def open_link_in_new_tab(driver, href):
    driver.execute_script("window.open(arguments[0], '_blank');", href)
    driver.switch_to.window(driver.window_handles[-1])


def login_to_cpanel(driver):
    login_button = driver.find_element(By.XPATH, "//button[contains(@onclick, 'singlesignon')]")
    login_button.click()

    WebDriverWait(driver, WAIT_TIME).until(expected_conditions.new_window_is_opened(driver.window_handles))
    driver.switch_to.window(driver.window_handles[-1])


def close_all_tabs_but_one(driver):

    main_window = driver.window_handles[0]

    for handle in driver.window_handles[1:]:
        driver.switch_to.window(handle)
        driver.close()

    driver.switch_to.window(main_window)


def write_to_file(list, filename):
    s = ""
    for entry in list:
        line = entry[0]
        for i in range(1, len(entry)):
            line += "," + entry[i]
        s += line + "\n"

    with open(filename, "w") as file:
        file.write(s)


def get_existing_applications():
    applications_list = []

    with open(APPLICATIONS_FILE, 'r') as file:
        for line in file:
            entry = line[:-1].split(',')
            applications_list.append(entry)
    if (len(applications_list) == 0):
        return [["Website Name", "Website URL", "Admin Email"]]
    else:
        return applications_list

def get_existing_domains():
    subdomains_list = []

    with open(DOMAINS_FILE, 'r') as file:
        for line in file:
            entry = line[:-1].split(',')
            subdomains_list.append(entry)
    if (len(subdomains_list) == 0):
        return [["Domain", "User", "Subdomain"]]
    else:
        return subdomains_list

def get_last_domain():
    arbitrary_big_number = 100000000000000 # arbitrary big number to start at beginning
    try:
        return int(open(LAST_DOMAIN_FILE, "r", encoding="UTF-8").readlines()[0])
    except:
        return arbitrary_big_number

def main():
    # See if user wants to reset files and start from the beginning
    if (len(sys.argv) == 2):
        if sys.argv[1] == "reset":
            write_to_file([], LAST_DOMAIN_FILE)
            write_to_file([], APPLICATIONS_FILE)
            write_to_file([], DOMAINS_FILE)

    last_domain = get_last_domain()
    applications_list = get_existing_applications()
    subdomains_list = get_existing_domains()

    driver = init_driver()

    username, password = get_credentials()
    login_to_WHMCS(driver, username, password)

    products_and_services_page_href = driver.find_element(By.ID, 'Menu-Clients-Products_Services').get_attribute('href')
    driver.get(products_and_services_page_href)

    for i in range(100): # I've set 100 as a safety number in case the loop doesn't stop for some reason

        # Get list of domains on current page, retry if theres a stale element reference exception
        for _ in range(5):
            try:
                links = driver.find_elements(By.CSS_SELECTOR, "#sortabletbl0 tr td:nth-child(2) a")

                domains = [(link.text, link.get_attribute("href")) for link in links]
                break
            except StaleElementReferenceException:
                continue
        
        for current_domain_id, href in domains:

            if (int(current_domain_id) >= last_domain):
                continue

            success = False
            for _ in range(2): 
                try:
                    close_all_tabs_but_one(driver)
                    print('Checking domain ' + current_domain_id)

                    open_link_in_new_tab(driver, href)

                    username = driver.find_element(By.ID, "inputUsername").get_attribute('value') # This will be useful for the subdomains list

                    login_to_cpanel(driver)

                    webscrape_cpanel(driver, applications_list, subdomains_list, username)

                    write_to_file(applications_list, APPLICATIONS_FILE)
                    write_to_file(subdomains_list, DOMAINS_FILE)
                    write_to_file([[current_domain_id]], LAST_DOMAIN_FILE)
                    success = True
                    break
                except StaleElementReferenceException:
                    continue
            if not success:
                raise Exception("Failed to scrape domain " + current_domain_id + " after multiple attempts.")
            
            # print('Checking domain ' + current_domain_id)

            # open_link_in_new_tab(driver, href)

            # username = driver.find_element(By.ID, "inputUsername").get_attribute('value') # This will be useful for the subdomains list

            # login_to_cpanel(driver)

            # webscrape_cpanel(driver, applications_list, subdomains_list, username)

            # write_to_file(applications_list, APPLICATIONS_FILE)
            # write_to_file(subdomains_list, DOMAINS_FILE)
            # write_to_file([[current_domain_id]], LAST_DOMAIN_FILE)

            # close_all_tabs_but_one(driver)

        try:
            next_page_link = driver.find_element(By.XPATH, "//a[contains(text(), 'Next Page')]")
            next_page_link.click()
        except:
            break


if __name__ == '__main__':
    main()