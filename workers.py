import requests
import lxml
from bs4 import BeautifulSoup
from random import randrange
from DO_NOT_PUSH_TO_GIT import aktirovki_url


class Parser(object):
    def __init__(self):
        pass

    @staticmethod
    def get_dayoff_info():
        page = requests.get(aktirovki_url)
        soup = BeautifulSoup(page.text, "lxml")
        div = soup.find("div", class_="activ")

        date = div.find("h3").text
        shifts = [elem.text for elem in div.find_all("p")]

        return date, shifts[0], shifts[1]
