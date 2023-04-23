import bs4
import urllib.request
import gzip
import os
import progress.bar
import sys
import concurrent.futures

CURL_FORMAT = "curl '{}' -H 'Accept-Encoding: gzip' -H 'Cookie: G_ENABLED_IDPS=google; sangeethamshare_login=svmhdvn%40gmail.com; PHPSESSID=f3sa8nki892brh2mk86m8ou47j; sessiontime=1682292771; G_AUTHUSER_H=0' -H 'Sec-Fetch-Site: same-origin' --output {}"

TEST_URL = 'https://www.sangeethamshare.org/tvg/UPLOADS-5801---6000/6000-Mannargudi_A_Easwaran-Layavinyasam-Adi_tALam/'

REQ_HEADERS = {
    'Accept-Encoding': 'gzip',
    'Cookie': 'G_ENABLED_IDPS=google; sangeethamshare_login=svmhdvn%40gmail.com; PHPSESSID=f3sa8nki892brh2mk86m8ou47j; sessiontime=1682303819; G_AUTHUSER_H=0',
    'Sec-Fetch-Site': 'same-origin'
}

def scrape_all_concerts_list():
    with open('concerts_raw.html') as f:
        soup = bs4.BeautifulSoup(f, 'html.parser')
        with open('all_concert_links.txt', 'w') as w:
            for a in soup.find_all(id='searchresults_table')[0].find_all('a'):
                w.write('{}\n'.format(a.attrs['href']))

def download_single_katcheri(link):
    dir_suffix = link.partition('https://sangeethamshare.org/')[-1].replace('/', '_')
    new_dir = os.path.join('all_concerts', dir_suffix)
    try:
        os.mkdir(new_dir)
    except FileExistsError:
        pass

    katcheri_html_path = os.path.join(new_dir, 'katcheri.html')
    if not os.path.exists(katcheri_html_path):
        req = urllib.request.Request(link, headers=REQ_HEADERS)
        try:
            with urllib.request.urlopen(req) as response:
                with open(katcheri_html_path, 'bw') as outfile:
                    outfile.write(gzip.decompress(response.read()))
        except urllib.error.HTTPError:
            print('broken: {}'.format(link))

def download_all_concerts():
    links = []
    with open('all_concert_links.txt') as f:
        links = [l.strip() for l in f]

    futures = []
    with concurrent.futures.ThreadPoolExecutor() as executor:
        for link in links:
            futures.append(executor.submit(download_single_katcheri, link))

        with progress.bar.Bar('Downloading', max=len(links)) as progress_bar:
            for future in concurrent.futures.as_completed(futures):
                progress_bar.next()

#scrape_all_concerts_list()
download_all_concerts()
