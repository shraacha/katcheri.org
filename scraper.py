import bs4
import concurrent.futures
import glob
import gzip
import os
import progress.bar
import sys
import urllib.request

COOKIE = 'G_ENABLED_IDPS=google; sangeethamshare_login=svmhdvn%40gmail.com; PHPSESSID=f3sa8nki892brh2mk86m8ou47j; sessiontime=1682303819; G_AUTHUSER_H=0'

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
        req = urllib.request.Request(link, headers={ 'Accept-Encoding': 'gzip', 'Cookie': COOKIE, 'Sec-Fetch-Site': 'same-origin' })
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

def download_single_mp3list(links_file):
    dirpath = os.path.dirname(links_file)
    with open(links_file) as f:
        for line in f:
            link = line.strip()

            filename = os.path.basename(link)
            mp3_local_path = os.path.join(dirpath, filename)
            if line != '' and not os.path.exists(mp3_local_path):
                req = urllib.request.Request(link, headers={ 'Cookie': COOKIE })
                try:
                    with urllib.request.urlopen(req) as response:
                        with open(mp3_local_path, 'bw') as outfile:
                            outfile.write(response.read())
                except urllib.error.HTTPError:
                    print('links_file: {}\tbroken_link: {}'.format(links_file, link))

def download_all_mp3s():
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
        all_mp3links_files = glob.glob('all_concerts/*/mp3links.txt')
        futures = []

        for links_file in all_mp3links_files:
            futures.append(executor.submit(download_single_mp3list, links_file))

        with progress.bar.Bar('Downloading mp3s', max=len(all_mp3links_files)) as progress_bar:
            for future in concurrent.futures.as_completed(futures):
                progress_bar.next()

#scrape_all_concerts_list()
#download_all_concerts()
download_all_mp3s()
