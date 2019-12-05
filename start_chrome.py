import os
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

from crawl.project02.config_parse import ConfigParser

config_parser = ConfigParser("config.txt")
cmd = config_parser.get_value("chrome") + " --remote-debugging-port=9222"
os.system(cmd)

