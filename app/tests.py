import configparser
import time

from django.apps import apps
from django.conf import settings
from django.contrib.auth.models import AnonymousUser, User
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from django.test import Client, RequestFactory, TestCase
from django.urls import reverse

from selenium import webdriver
from selenium.common.exceptions import StaleElementReferenceException, TimeoutException
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.edge.service import Service as EdgeService
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from webdriver_manager.chrome import ChromeDriverManager
from webdriver_manager.microsoft import EdgeChromiumDriverManager

# Access configparser to load variable values
config = configparser.SafeConfigParser(allow_no_value=True)
config.read('%s/settings.ini' % (settings.BASE_DIR / 'dashboard'))

class SeleniumTestsChromeBase(StaticLiveServerTestCase):

    # def test_driver_manager_chrome(self):
    #     service = ChromeService(executable_path=ChromeDriverManager().install())
    #     driver = webdriver.Chrome(service=service)
    #     driver.quit()

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        service = ChromeService(executable_path=ChromeDriverManager().install())
        cls.selenium = webdriver.Chrome(service=service)
        cls.selenium.implicitly_wait(10)
        cls.USERNAME = config['settings']['AQUAREA_USR']
        cls.PASSWORD = config['settings']['AQUAREA_PWD']
        cls.host_tobe_tested = cls.live_server_url

    @classmethod
    def tearDownClass(cls):
        cls.selenium.quit()
        super().tearDownClass()

    def test_driver_manager_chrome(self):
        service = ChromeService(executable_path=ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service)
        driver.quit()

    def test_aquarea_service_login(self):
        self.selenium.get("https://aquarea-service.panasonic.com/")
        username_input = self.selenium.find_element(By.ID, "login-id")
        username_input.send_keys(self.USERNAME)
        password_input = self.selenium.find_element(By.ID, "login-pw")
        password_input.send_keys(self.PASSWORD)
        time.sleep(3)
        self.selenium.find_element(By.XPATH, '//input[@value="Login"]').click()
        time.sleep(3)

