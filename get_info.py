# -*- coding: UTF-8 -*-.

import requests
import lxml
from bs4 import BeautifulSoup
from DO_NOT_PUSH_TO_GIT import aktirovki_url


def get_():
    page = requests.get(aktirovki_url)
    soup = BeautifulSoup(page.text, "lxml")
    div = soup.find("div", class_="activ")

    date = div.find("h3").text
    shifts = [elem.text for elem in div.find_all("p")]

    print(date, shifts[0], shifts[1])
    return date, shifts[0], shifts[1]

