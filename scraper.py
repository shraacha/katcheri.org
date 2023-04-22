from bs4 import BeautifulSoup

soup = None

with open('concerts_raw.html') as fp:
    soup = BeautifulSoup(fp, 'html.parser')
