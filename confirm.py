import os
import json
import datetime
import pandas as pd

from time import sleep, time
from selenium import webdriver
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By

from functions import get_captcha, captcha_is_invalid, post, solve_captcha

DRIVER = ChromeDriverManager().install()
INIT_URL = 'https://q.midpass.ru/'

# Start driver in a headless mode

chrome_options = Options()
chrome_options.add_argument("--headless")
prefs = {'download.default_directory' : os.getcwd()}
chrome_options.add_experimental_option('prefs', prefs)
driver = webdriver.Chrome(DRIVER, chrome_options=chrome_options)

# Try to log in into 

success = False
driver.get(INIT_URL)

while not success: 

    # Reftesh captcha untill valid result

    driver.execute_script("RefreshCaptcha();")
    captcha = get_captcha(driver)

    if captcha_is_invalid(captcha):
        continue

    # If valid try to log in
    print(f'Login attempt: {captcha}')

    request_data = {
        'NeedShowBlockWithServiceProviderAndCountry': True,
        'CountryId': os.environ['CountryId'],
        'ServiceProviderId': os.environ['ServiceProviderId'],
        'Email': os.environ['Email'],
        'g-recaptcha-response':'', 
        'Captcha': captcha,
        'Password': os.environ['Password'],
    }

    post(path = 'https://q.midpass.ru/ru/Account/DoPrivatePersonLogOn', params=request_data)

    # If unsucccessfull refresh captcha and try again
    # Ususally take 2-3 attempts

    success = ('DoPrivatePersonLogOn' not in driver.current_url)


# Check if request can be confirmed. If not wait 5 min and try again

can_confirm = False

while not can_confirm:

    request_data = {
        'begin':0,
        'end':10
    }

    post(
        path = 'https://q.midpass.ru/ru/Appointments/FindWaitingAppointments', 
        params=request_data,
        driver = driver
        )
    json_result = json.loads(driver.find_element(By.TAG_NAME, 'pre').text)

    can_confirm = json_result['Items'][0]['CanConfirm']
    place_in_queue = json_result['Items'][0]['PlaceInQueue']

    print(f'Place in queue: {place_in_queue}')
    print(f'Can confirm: {can_confirm}')

    if not can_confirm:
        sleep(60*5)

# write position in queue to trace progress

queue_records = pd.read_excel('queue.xlsx', engine = 'openpyxl')
today_record = pd.DataFrame({'date': [datetime.datetime.now().strftime("%Y-%m-%d")], 'place' : [place_in_queue]})
queue_records = pd.concat([queue_records, today_record])
queue_records.to_excel('queue.xlsx')

# If can be confirmed, refresh the captcha and try to sent confirmation request

success = False

while not success:

    driver.get(f'https://q.midpass.ru/ru/Appointments/CaptchaImage?{int(time()*1000)}')
    sleep(1)
    os.remove('Captcha(1).jpg')
    os.rename(os.getcwd()+'\Captcha', 'Captcha.jpg')

    captcha = solve_captcha('Captcha.jpg')

    if captcha_is_invalid(captcha):
        continue

    print(f'Subittion attempt: {captcha}')

    request_data = {
        'ids':os.environ['req_id'],
        'captcha':captcha
        }

    post(
        path = 'https://q.midpass.ru/ru/Appointments/ConfirmWaitingAppointments', 
        params=request_data, 
        driver = driver
    )

    json_result = json.loads(driver.find_element(By.TAG_NAME,'pre').text)
    success = json_result['IsSuccessful']

print('Submitted successfully')