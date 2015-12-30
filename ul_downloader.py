#!/usr/bin/env python3

"""This Script can be used to download all files contained in a dlc-file. For
personal use only.

Usage: ul-downloader [args] <dlc-file>
"""

#TODO: Concurrent Downloads??

import argparse
import base64
from codecs import decode, encode
from Crypto.Cipher import AES
import datetime
from os.path import devnull, expanduser, getsize, exists
import re
import requests
import sys
import xml.etree.ElementTree as ElementTree

KEY = "cb99b5cbc24db398"
IV = "9bc24cb995cb8db3"
API_URL = "http://service.jdownloader.org/dlcrypt/\
service.php?srcType=dlc&destType=pylo&data=%s"

def get_dlc_data(dlc_file):

    try:
        with open(dlc_file, 'r') as dlc:
            dlc_cont = dlc.read().strip()
    except FileNotFoundError:
        print('Error found while processing file, exiting ...')
        exit(1)

    dlc_key = dlc_cont[-88:]
    dlc_data = decode(dlc_cont[:-88].encode('ascii'), 'base64')
    dlc_content = requests.get(API_URL % dlc_key).text.replace(
        '<rc>', '').replace('</rc>', '')

    key = AES.new(KEY, AES.MODE_CBC, IV).decrypt(
        decode(dlc_content.encode('ascii'), 'base64'))
    data = decode(AES.new(key, AES.MODE_CBC, key).decrypt(dlc_data), 'base64')
    return decode(data, 'utf-8')


def get_links(dlc_data):

    links = []
    dlc_root = ElementTree.fromstring(dlc_data)
    for x in dlc_root.findall('content/package/file'):
        url = decode(
            x.find('url').text.encode('ascii'), 'base64').decode('utf-8')
        links.append(url)
    return links


def download_files(links):

    payload = {}
    with open(expanduser('~') + '/.config.ug', 'r') as config_file:
        for line in config_file.readlines():
            payload[line.split('=')[0]] = line.split('=')[1]
    uploaded_login = requests.post(
        'http://uploaded.net/io/login', data=payload)
    uploaded_login.raise_for_status()
    for link in links:
        if not ('ul.' in link or 'uploaded.' in link):
            print('omitting file:', link)
            print('no vaid uploaded.net-link')
            continue
        print('Processing', link, '...')
        file_request = requests.get(link, cookies=uploaded_login.cookies)
        pattern = 'action=\".*?\"'
        regex = re.compile(pattern)
        match = regex.search(file_request.text)
        try:
            dl_url = match.group().replace('action=', '').replace('"', '')
            dl_request = requests.get(dl_url, stream=True, verify=False)
            filename = dl_request.headers['content-disposition'].split('"')[1]
            print('Filename:', filename)
            full_size = int(dl_request.headers['content-length'])
            if exists(
                './' + filename) and getsize('./' + filename) == full_size:
                print('File', filename, 'is already downloaded, omitting...')
                continue
            with open('./' + filename, 'wb') as output_file:
                for chunk in dl_request.iter_content(chunk_size=1024):
                    filesize = getsize('./' + filename)
                    update_progress(int(filesize / full_size * 100))
                    if chunk:
                        output_file.write(chunk)
                        output_file.flush()
            update_progress(100)
        except AttributeError as e:
            print(e)
        print('\n')


def update_progress(progress):

    if progress % 2 == 0:
        print('\r[ {0} ] {1}%'.format(
            '=' * int(progress/2) + ' ' * (
            50 - int(progress/2)), progress), end='')
    else:
        print('\r[ {0} ] {1}%'.format(
            '='*int(progress/2) + '-' + ' ' * (
            49 - int(progress/2)), progress), end='')


def main(dlc_file):

    dlc_data = get_dlc_data(dlc_file)
    links = get_links(dlc_data)
    download_files(links)


if __name__ == '__main__':

    parser = argparse.ArgumentParser()
    parser.add_argument('-l', '--download_list',
        help='Download a file that contains a list of links.',
        action='store_true')
    parser.add_argument('-q', '--quiet',
        help='surpress programm output to stdout', action='store_true')
    parser.add_argument('file', help='File that contains relevant data')
    args = parser.parse_args()

    if args.quiet:
        sys.stdout = open(devnull, 'w')

    if args.download_list:
        try:
            link_file = open(args.file, 'r')
            links = [x.rstrip() for x in link_file.readlines()]
            download_files(links)
            link_file.close()
        except KeyboardInterrupt:
            print('\nProgram killed by user.')
        except Exception as e:
            print('\nInternal Error occured:')
            print(e)
    else:
        try:
            main(args.file)
        except KeyboardInterrupt:
            print('\nProgram killed by user.')
        except Exception as e:
            print('\nInternal Error occured:')
            print(e)
