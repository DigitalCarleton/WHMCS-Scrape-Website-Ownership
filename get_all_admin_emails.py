import sys
from selenium.webdriver import Chrome
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions

WAIT_TIME = 10
ERRORS_FILE = 'out/errors.txt'
EMAILS_FILE = 'out/admin_emails.csv'

# Adds admin email and domain of each app to emails_dict
# Returns a list of all apps with an error
def get_admin_emails_from_cpanel(driver, emails_dict):
    try:
        driver.find_element(By.ID, 'item_myapps').click()
    except:
        try:
            # sometimes there is a Jupiter pop up window that must be closed
            driver.find_element(By.ID, 'btnSetupLater').click() # TODO - necessary? only happened twice
            driver.find_element(By.ID, 'item_myapps').click()
        except:
            return ['Domain Error']

    num_apps = driver.find_element(By.ID, 'i_header_tab_installs_num').text
    if (num_apps == '0'):
        return []

    wrench_links = driver.find_elements(By.XPATH, "//a[.//div[contains(@class, 'i_icon_edit') and contains(., 'Edit')]]")

    apps_tab = driver.current_window_handle
    
    erroneous_apps = []
    app_count = 1

    for link in wrench_links:

        open_link_in_new_tab(driver, link.get_attribute('href'))

        try:
            settings_button = driver.find_element(By.XPATH, "//a[contains(@href, '/settings') and normalize-space()='Settings']")
            settings_button.click()
            
            website_url = driver.find_element(By.ID, 'field_url').find_element(By.TAG_NAME, 'option').text

            application_button = driver.find_element(By.XPATH, "//a[.//div[normalize-space()='Application']]")
            application_button.click()

            admin_email = driver.find_element(By.ID, 'field_email').get_attribute('value')

            add_email_and_website_to_dict(emails_dict, admin_email, website_url[7:])
        except:
            erroneous_apps.append(app_count)

        app_count += 1
        
        driver.switch_to.window(apps_tab)

    return erroneous_apps


def add_email_and_website_to_dict(emails_dict, new_email, new_website):
    if new_email in emails_dict:
        emails_dict[new_email].append(new_website)
    else:
        emails_dict[new_email] = [new_website]


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


def close_all_tabs_except(driver, tab_index):

    num_tabs = len(driver.window_handles)
    
    for i in range(num_tabs):
        index = num_tabs - i - 1
        if (index != tab_index):
            driver.switch_to.window(driver.window_handles[num_tabs - i -1])
            driver.close()
    
    driver.switch_to.window(driver.window_handles[0])


def write_emails_to_file(emails_dict, filename):
    s = ""
    for key in emails_dict:
        line = key
        for value in emails_dict[key]:
            line += "," + value
        s += line + "\n"

    with open(filename, "w") as file:
        file.write(s)


def append_errors_to_file(domain_id, erraneous_apps_list, filename):
    s = f'Error(s) in domain {domain_id}\nThere are errors in the following apps: '
    for app in erraneous_apps_list:
        s += f'{app} '
    s+= '\n\n'

    with open(filename, "a") as file:
        file.write(s)


def get_existing_emails(filename):
    emails_dict = {}

    with open(filename, 'r') as file:
        for line in file:
            entry = line[:-1].split(',')
            emails_dict[entry[0]] = entry[1:]
    
    return emails_dict


def main():
    start_domain_id = 1000000 # arbitrary big number to start at beginning

    # See if user wants to start at a particular domain
    if (len(sys.argv) == 2):
        start_domain_id = int(sys.argv[1])

    
    username, password = get_credentials()

    driver = init_driver()

    login_to_WHMCS(driver, username, password)

    products_and_services_page_href = driver.find_element(By.ID, 'Menu-Clients-Products_Services').get_attribute('href')
    driver.get(products_and_services_page_href)

    emails_dict = get_existing_emails(EMAILS_FILE)

    for i in range(100): # I've set 100 as a safety number in case the loop doesn't stop for some reason

        WebDriverWait(driver, WAIT_TIME).until(
            expected_conditions.presence_of_element_located((By.ID, "sortabletbl0"))
        )
                
        rows = driver.find_element(By.ID, "sortabletbl0").find_elements(By.CSS_SELECTOR, "tr")[1:]

        domains = []
        for row in rows:
            link = row.find_element(By.CSS_SELECTOR, "a")
            domains.append((link.text, link.get_attribute('href')))
        
        for current_domain_id, href in domains:

            if (int(current_domain_id) > start_domain_id):
                continue

            print('Checking domain ' + current_domain_id)

            open_link_in_new_tab(driver, href)

            login_to_cpanel(driver)

            apps_with_errors = get_admin_emails_from_cpanel(driver, emails_dict)

            if (len(apps_with_errors) > 0):
                append_errors_to_file(current_domain_id, apps_with_errors, ERRORS_FILE)
                
            write_emails_to_file(emails_dict, EMAILS_FILE)

            close_all_tabs_except(driver, tab_index=0)

        try:
            next_page_link = driver.find_element(By.PARTIAL_LINK_TEXT, "Next Page")
            next_page_link.click()
        except:
            break


if __name__ == '__main__':
    main()