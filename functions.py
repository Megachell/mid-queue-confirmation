import numpy as np
from PIL import  Image
from selenium.webdriver.common.by import By
import cv2
import re

def post(path, params, driver):
    driver.execute_script("""
    function post(path, params, method='post') {
        const form = document.createElement('form');
        form.method = method;
        form.action = path;
    
        for (const key in params) {
            if (params.hasOwnProperty(key)) {
            const hiddenField = document.createElement('input');
            hiddenField.type = 'hidden';
            hiddenField.name = key;
            hiddenField.value = params[key];
    
            form.appendChild(hiddenField);
        }
        }
    
        document.body.appendChild(form);
        form.submit();
    }
    
    post(arguments[1], arguments[0]);
    """, params, path)



def remove_bg(input_img):
    default_vec = np.array([150, 150, 150])
    img = input_img.copy()
    for i in range(0, img.shape[0]):
        for j in range(0, img.shape[1]):
            if np.linalg.norm(img[i][j][0:3] - default_vec) > 70:
                img[i][j][0:3] = [255,255,255]
    return img


def get_letter_and_crop(img):

    results = dict()
    cutoffs = dict()

    for letter in 'abcdefghijklmnopqrstuvwxyz':

        template = cv2.imread(f'letters/{letter}.png', 0)
        height, width = template.shape[::]

        res = cv2.matchTemplate(img, template, cv2.TM_CCOEFF_NORMED)
        threshold = 0.5
        detected = np.where( res[34-height-2:34-height+2,:] >= threshold)[0]

        if len(detected) != 0 :
            if 0 < detected[0] < 25 :
                results[letter] = res[34-height,:].max()
                cutoffs[letter] = detected[0] + width - 5

    if len(results.keys()) == 0:
        return '', img

    letter_max = max(results, key=results.get)

    cutoff = cutoffs[letter_max]
    img = img[:,cutoff:]

    return letter_max, img


def get_number_and_crop(input_img):

    found = True
    digit_string = ''
    while found:
        results = dict()
        cutoffs = dict()

        for digit in '1234567890':

            template = cv2.imread(f'letters/{digit}.png', 0)
            height, width = template.shape[::]

            res = cv2.matchTemplate(input_img, template, cv2.TM_CCOEFF_NORMED)
            threshold = 0.5
            detected = np.where( res[12:15,:] >= threshold)[1]

            if len(detected) != 0 :
                results[digit] = res[13,:].max()
                cutoffs[digit] = detected[0] + width - 5

        results = {k:results[k] for k in results if cutoffs[k] < 25}
        found = len(results.keys()) > 0

        if found:

            digit_max = max(results, key=results.get)
            cutoff = cutoffs[digit_max]
            input_img = input_img[:,cutoff:]

            digit_string += digit_max

    return digit_string


def solve_capcha(name):

    img_rgb = Image.open(name)

    factor = 46 / img_rgb.size[1]
    img_rgb = img_rgb.resize((int(img_rgb.size[0] * factor), int(img_rgb.size[1] * factor)))
    img_rgb = np.array(img_rgb)*255


    img_rgb = remove_bg(img_rgb)
    img_gray = cv2.cvtColor(img_rgb, cv2.COLOR_BGR2GRAY)

    first_letter, img_res = get_letter_and_crop(img_gray)

    digit_string = get_number_and_crop(img_res)

    return first_letter+digit_string


def get_capcha(driver):

    img = driver.find_element(By.ID ,'imgCaptcha')

    driver.execute_script("arguments[0].scrollIntoView();", img)

    img.screenshot('capcha.png')

    return solve_capcha('capcha.png')

def captcha_is_invalid(s):
    return re.search(r'[a-z][0-9]{5}', s) is None