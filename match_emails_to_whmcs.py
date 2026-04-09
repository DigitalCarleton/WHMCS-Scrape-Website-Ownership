import sys
import config
from selenium.webdriver import Chrome
from selenium.webdriver.common.by import By

# Updates user notes
# Returns emails without a user profile
def perform_match(list1, list2):
    users_without_profile = []
    for item in list1:
        if item not in list2:
            users_without_profile.append(item)

    return users_without_profile

def init_driver():
    driver = Chrome()
    driver.get("https://sites.carleton.edu/manage/whmcs-admin/login.php?logout=1")
    driver.implicitly_wait(5)
    return driver


def login_to_WHMCS(driver):
    driver.find_element(By.NAME, 'username').send_keys(config.username)
    driver.find_element(By.NAME,'password').send_keys(config.password)
    driver.find_element(By.CSS_SELECTOR,'input[value=Login]').click()


def get_emails_from_file(filename):
    emails_list = []

    with open(filename, 'r') as file:
        for line in file:
            emails_list.append(line.split(',')[0])
    
    return emails_list


def main():
    admin_emails = get_emails_from_file(sys.argv[1])
    whmcs_user_emails = []

    driver = init_driver()

    login_to_WHMCS(driver)

    clients_menu_item = driver.find_element(By.ID, 'Menu-Clients')
    clients_menu_item.click()

    # enables the view of inactive accounts
    driver.find_element(By.CLASS_NAME, 'bootstrap-switch').click()

    for i in range(100): # I've set 100 as a safety number in case the loop doesn't stop for some reason

        user_rows = driver.find_element(By.ID, "sortabletbl0").find_elements(By.CSS_SELECTOR, "tr")[1:]
        for user in user_rows:
            email_address = user.find_elements(By.CSS_SELECTOR, "a")[3].text
            whmcs_user_emails.append(email_address)

        try:
            next_page_link = driver.find_element(By.PARTIAL_LINK_TEXT, "Next Page")
            next_page_link.click()
        except:
            break

    users_without_profile = perform_match(admin_emails, whmcs_user_emails)
    print(users_without_profile)


if __name__ == '__main__':
    main()