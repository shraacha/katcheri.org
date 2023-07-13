import base64
import re
import binascii
import bs4
import concurrent.futures
import csv
import glob
import gzip
import os
import progress.bar
import sys
import urllib.parse
import urllib.request

COOKIE = 'G_ENABLED_IDPS=google; sangeethamshare_login=svmhdvn%40gmail.com; PHPSESSID=3gio1a67gp42tetn0mbmm9sgbh; sessiontime=1688702634; G_AUTHUSER_H=0'

PLAYPAUSE_HREF_REGEX = re.compile(re.escape('http://pdx.ravisnet.com:8080/player2.php'))

ALL_AUDIO_LINKS = 'all_audio_links.csv'
ALL_CONCERT_LINKS = 'all_concert_links.csv'
ARIA_INPUT = 'aria_download_list.txt'
INVALID_LINKS = 'todo_investigate/invalid_links.txt'

# TODO find some way to validate each link
# currently, I'm doing a quick (1 min) manual validation pass over the links and
# putting any definitely-broken links into another file
def scrape_all_concerts_list():
    with open('concerts_raw.html') as f:
        soup = bs4.BeautifulSoup(f, 'html.parser')
        with open(ALL_CONCERT_LINKS, 'w', newline='', encoding='utf-8') as w:
            linkwriter = csv.DictWriter(w, fieldnames=['url', 'output_dir'])
            linkwriter.writeheader()

            # unique sorted list of all concerts
            hrefs = sorted(set([a.attrs['href'] for a in soup.find_all(id='searchresults_table')[0].find_all('a')]))
            for href in hrefs:
                # outputs a CRC32 in hex without the leading '0x' prefix
                crc32 = hex(binascii.crc32(href.encode('utf8')))[2:]
                
                # strips off trailing slash and gives just the last component of the URL
                last_component = os.path.basename(os.path.normpath(href))

                linkwriter.writerow({'url': href, 'output_dir': '{}-{}'.format(crc32, last_component)})

def download_single_katcheri(link_row, invalid_links_file):
    new_dir = os.path.join('all_concerts', link_row['output_dir'])
    try:
        os.mkdir(new_dir)
    except FileExistsError:
        pass

    katcheri_html_path = os.path.join(new_dir, 'katcheri.html')
    if not os.path.exists(katcheri_html_path):
        req = urllib.request.Request(link_row['url'], headers={ 'Accept-Encoding': 'gzip', 'Cookie': COOKIE, 'Sec-Fetch-Site': 'same-origin' })
        try:
            with urllib.request.urlopen(req) as response:
                with open(katcheri_html_path, 'bw') as outfile:
                    outfile.write(gzip.decompress(response.read()))
        except urllib.error.HTTPError:
            print('broken: {}'.format(link_row), file=invalid_links_file)

def download_all_concerts():
    links = []
    with open('all_concert_links.csv', newline='') as f:
        linkreader = csv.DictReader(f)
        for row in linkreader:
            links.append(row)

    futures = []
    with open(INVALID_LINKS, 'w') as invalid_links_file:
        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
            for row in links:
                futures.append(executor.submit(download_single_katcheri, row, invalid_links_file))

            with progress.bar.Bar('Downloading', max=len(links)) as progress_bar:
                for future in concurrent.futures.as_completed(futures):
                    progress_bar.next()

def parse_audio_links():
    with open(ALL_AUDIO_LINKS, 'w', newline='') as w:
        linkwriter = csv.DictWriter(w, fieldnames=['filename', 'url', 'output_dir'])
        linkwriter.writeheader()

        all_katcheris = glob.glob('all_concerts/*/katcheri.html')
        for katcheri in all_katcheris:
            with open(katcheri) as kf:
                try:
                    soup = bs4.BeautifulSoup(kf, 'html.parser')
                    playpause_links = [a['href'] for a in soup.find_all('a', class_='playpause', href=PLAYPAUSE_HREF_REGEX)]
                    for link in playpause_links:
                        try:
                            # each link is in this form:
                            # 'http://pdx.ravisnet.com:8080/player2.php?b=<base64 encoded directory>&t=<base64 encoded audio filename>'
                            # parse the 'b=<val>' and 't=<val>' params
                            parsed_link = urllib.parse.urlparse(link)
                            query_params = urllib.parse.parse_qs(parsed_link.query)
                            audio_directory = base64.b64decode(query_params['b'][0]).decode('utf8')
                            audio_filename = base64.b64decode(query_params['t'][0]).decode('utf8')
                            linkwriter.writerow({
                                'filename': audio_filename,
                                'url': os.path.join('http://pdx.ravisnet.com:8080/', audio_directory, audio_filename),
                                'output_dir': os.path.dirname(katcheri)
                            })
                        except Exception as e:
                            print('PLAYPAUSE LINK ERROR: {}'.format(e))
                            print('\tfailing link: {}'.format(link))
                            print()
                except Exception as e:
                    print('KATCHERI ERROR: {}'.format(e))
                    print('\tfailing katcheri file: {}'.format(katcheri))
                    print()

def generate_aria2_from_csv():
    with open(ALL_AUDIO_LINKS, newline='') as f:
        linkreader = csv.DictReader(f)
        with open(ARIA_INPUT, 'w') as aria:
            for row in linkreader:
                aria.write('{}\n  dir={}\n  out={}\n'.format(row['url'], row['output_dir'], row['filename']))

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
#download_all_mp3s()
#parse_audio_links()
generate_aria2_from_csv()
