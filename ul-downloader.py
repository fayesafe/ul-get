#!/usr/bin/env python3

"""This Script can be used to download all files contained in a dlc-file. For
personal use only.

Usage: ul-downloader <dlc-file>
"""

#TODO: DL-Continue, Concurrent DL

import base64
from codecs import decode, encode
from collections import namedtuple
from Crypto.Cipher import AES
import datetime
from os.path import expanduser
import re
import requests
import sys
import xml.etree.ElementTree as ElementTree

KEY = "cb99b5cbc24db398"
IV = "9bc24cb995cb8db3"
API_URL = "http://service.jdownloader.org/dlcrypt/service.php?srcType=dlc&destType=pylo&data=%s"

def get_dlc_data(dlc_file):

	try:
		with open(dlc_file) as dlc:
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

	Link = namedtuple('Link', ['filename', 'url'])
	links = []
	dlc_root = ElementTree.fromstring(dlc_data)
	for x in dlc_root.findall('content/package/file'):
		url = decode(
			x.find('url').text.encode('ascii'), 'base64').decode('utf-8')
		try:
			filename = decode(x.find(
				'filename').text.encode('utf-8'), 'base64').decode('utf-8')

		# if filename is not specified within the dlc
		# get it from the ul-page

		except AttributeError:
			page_dl = requests.get(url)
			pattern = '<a .*? id=\"filename\".*?>.*?</a>'
			filename_regex = re.compile(pattern)
			match = filename_regex.search(page_dl.text)
			try:
				filename = match.group().split('>')[1].split('<')[0]
			except AttributeError:
				filename = 'file' + str(datetime.datetime.now())
		links.append(Link(filename=filename, url=url))
	return links


def download_files(links):

	payload = { }
	with open(expanduser('~') + '/.config.ug', 'r') as config_file:
		for line in config_file.readlines():
			payload[line.split('=')[0]] = line.split('=')[1]
	uploaded_login = requests.post('http://uploaded.net/io/login', data=payload)
	uploaded_login.raise_for_status()
	for link in links:
		if not ('ul' in link.url or 'uploaded' in link.url):
			continue
		print('Processing', link.filename, link.url, '...')
		file_request = requests.get(link.url, cookies=uploaded_login.cookies)
		pattern = 'action=\".*?\"'
		regex = re.compile(pattern)
		match = regex.search(file_request.text)
		try:
			dl_url = match.group().replace('action=', '').replace('"', '')
			dl_request = requests.get(dl_url, stream=True)
			with open('./' + link.filename, 'wb') as output_file:
				for chunk in dl_request.iter_content(chunk_size=1024):
					if chunk:
						output_file.write(chunk)
						output_file.flush()
		except AttributeError as e:
			print(e)
		print('... Done.')


def main(dlc_files):

	for dlc_file in dlc_files:
		dlc_data = get_dlc_data(dlc_file)
		links = get_links(dlc_data)
		download_files(links)


if __name__ == '__main__':
	if len(sys.argv) > 1:
		main(sys.argv[1:])
	else:
		print('No DLC-File found, exiting ...')
		print('ul-downloader <dlc-file>')
		exit(1)
