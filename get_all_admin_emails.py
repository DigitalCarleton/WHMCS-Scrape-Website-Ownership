import sys
import config
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

    wrench_links = driver.find_elements(By.CSS_SELECTOR, "a[data-descr='View/edit details']")

    apps_tab = driver.window_handles[-1]
    
    erroneous_apps = []
    app_count = 1

    for link in wrench_links:

        open_link_in_new_tab(driver, link.get_attribute('href'))

        try:
            admin_email = driver.find_element(By.ID, 'field_email').get_attribute('value')

            advanced_tab = driver.find_element(By.ID, 'i_app_subtabs_2')
            advanced_tab.click()

            website_url = driver.find_element(By.ID, 'field_url').find_element(By.TAG_NAME, 'option').text

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


def login_to_WHMCS(driver):
    driver.find_element(By.NAME, 'username').send_keys(config.username)
    driver.find_element(By.NAME,'password').send_keys(config.password)
    driver.find_element(By.CSS_SELECTOR,'input[value=Login]').click()


def open_link_in_new_tab(driver, href):
    driver.execute_script("window.open(arguments[0], '_blank');", href)
    driver.switch_to.window(driver.window_handles[-1])


def login_to_cpanel(driver):
    login_button = driver.find_element(By.XPATH, '//button[normalize-space()="Login to cPanel"]')
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
        start_domain_id = sys.argv[2]

    driver = init_driver()

    login_to_WHMCS(driver)

    products_and_services_page_href = driver.find_element(By.ID, 'Menu-Clients-Products_Services').get_attribute('href')
    driver.get(products_and_services_page_href)

    emails_dict = get_existing_emails(EMAILS_FILE)

    for i in range(100): # I've set 100 as a safety number in case the loop doesn't stop for some reason

        all_domain_rows = driver.find_element(By.ID, "sortabletbl0").find_elements(By.CSS_SELECTOR, "tr")[1:]

        for domain_row in all_domain_rows:

            domain_id_link = domain_row.find_element(By.CSS_SELECTOR, "a")
            current_domain_id = domain_id_link.text

            if (int(current_domain_id) > start_domain_id):
                continue

            print('Checking domain ' + current_domain_id)

            open_link_in_new_tab(driver, domain_id_link.get_attribute('href'))

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