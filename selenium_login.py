# Selenium login utility
# Copyright (c) 2022 Warren Usui
# This code is licensed under the MIT license (see LICENSE.txt for details)
"""
Selenium webpage login utility
"""
import os
import configparser
import yaml
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager

def selenium_login(in_dir):
    """
    Login to a webpage using selenium

    Input parameter:
        Path to a directory that contains the following files:
            secret.ini
            fields.yaml
        Secret.ini contain entries for you username and password
        Fields.yaml contains the url for the login site and field types
        and identifiers for the name, password, and submit button on the
        login site.

    Returns:
        Webdriver on success
        List of errors on failure
        
    Note that success and failure are also displayed by the behavior
    of the web browser.
    """
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()))

    secret_info = configparser.ConfigParser()
    secret_info.read(os.sep.join([in_dir, "secret.ini"]))

    user = secret_info["DEFAULT"]["username"]
    pwrd = secret_info["DEFAULT"]["password"]

    with open(os.sep.join([in_dir, "fields.yaml"]),
              "r", encoding="utf8") as infile:
        try:
            ydata = yaml.safe_load(infile)
        except yaml.YAMLError as exc:
            print(exc)

    driver.get(ydata["url"])
    driver.find_element(ydata["usertype"], ydata["uservar"]).send_keys(user)
    driver.find_element(ydata["passtype"], ydata["passvar"]).send_keys(pwrd)
    driver.find_element(ydata["buttontype"], ydata["buttonvar"]).click()

    WebDriverWait(driver=driver, timeout=10).until(
        lambda x: x.execute_script(
            "return document.readyState === 'complete'"
        )
    )
    errors = driver.find_elements(By.CLASS_NAME, "flash-error")
    if errors:
        return errors
    return driver
