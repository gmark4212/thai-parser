#!/usr/bin/python
# -*- coding: utf-8 -*-
import os
import errno
import requests
import random
import time
from bs4 import BeautifulSoup
from sqlalchemy.orm import sessionmaker
from models import DB_ENGINE, IMG_PATH, Products
from googletrans import Translator
from settings import USER_AGENTS
from lxml.html import fromstring


class BaseParser:
	def __init__(self):
		self.engine = DB_ENGINE
		sess = sessionmaker(self.engine)
		self.session = sess()
		self.translator = Translator()
		self.proxies = []
		self.default_root = 'https://free-proxy-list.net/'

	def _commit(self):
		self.session.commit()

	def _add_to_session(self, obj):
		self.session.add(obj)
		self._commit()

	def fetch_proxies(self):
		print('Begin to collect zombie-list')
		response = requests.get('https://free-proxy-list.net/')
		parser = fromstring(response.text)
		for i in parser.xpath('//tbody/tr')[:20]:
			if i.xpath('.//td[7][contains(text(),"yes")]'):
				proxy = ":".join([i.xpath('.//td[1]/text()')[0], i.xpath('.//td[2]/text()')[0]])
				self.proxies.append(proxy)
		primary_count = len(self.proxies)
		self.test_proxilist()
		print('PROXIES CHARGED: collected: {}, survived: {} '.format(primary_count, len(self.proxies)))

	def test_proxilist(self):
		for proxy in self.proxies:
			try:
				response = requests.get(self.default_root, proxies={"http": proxy, "https": proxy})
			except:
				print('Proxy {} deleted'.format(proxy))
				self.proxies[self.proxies.index(proxy)] = None
			self.proxies = [x for x in self.proxies if bool(x)]

	def get_random_proxy(self):
		if len(self.proxies) == 0:
			print('PROXY LIST IS EMPTY! I AM GETTING NEW...')
			self.fetch_proxies()
		proxy_index = random.randint(0, len(self.proxies) - 1)
		proxy = self.proxies[proxy_index]
		return proxy

	def store_img_locally(self, img_url=None):
		if img_url:
			path = img_url.replace(self.static_url,'')
			path = os.path.join(self.img_dir, path)
			if not os.path.exists(os.path.dirname(path)):
				try:
					os.makedirs(os.path.dirname(path))
				except OSError as exc:  # Guard against race condition
					if exc.errno != errno.EEXIST:
						raise
			with open(path, 'wb') as handle:
				headers = {'User-Agent': self.get_random_user_agent()}
				response = requests.get(img_url, stream=True, headers=headers)
				if not response.ok:
					print(response)
				for block in response.iter_content(1024):
					if not block:
						break
					handle.write(block)
			return path

	def translate(self, text):
		if text:
			return self.translator.translate(text, src='en', dest='ru').text

	def save_product(self, product=None):
		if product:
			self._add_to_session(Products(**product))

	def get_random_user_agent(self):
		return USER_AGENTS[random.randint(0, len(USER_AGENTS)-1)]

	def get_random_delay(self):
		return random.randint(1, 3)

	def gettext(self, obj):
		if obj is None:
			return ''
		else:
			return obj.get_text()

	def product_exists_in_db(self, sku=None, name=None):
		if sku:
			_by_sku = self.session.query(Products).filter(Products.sku == sku).first()
		if name and _by_sku is None:
			_by_name = self.session.query(Products).filter(Products.name == name).first()
		exist = bool(_by_sku) or bool(_by_name)
		if exist:
			print('EXIST: ', sku, name)
		return exist

	def this_url_parsed_already(self, url=None):
		return bool(self.session.query(Products).filter(Products.product_url == url).first())

	def __del__(self):
		if self.session is not None:
			try:
				self.session.close()
			except:
				pass


class Tesco(BaseParser):
	# https://shoponline.tescolotus.com/groceries/en-GB/shop/beverages-snacks-and-desserts/snacks/all
	def __init__(self):
		self.id = 3


class Makro(BaseParser):
	# https://www.makroclick.com/en/category/snack
	def __init__(self):
		self.id = 2


class Bigc(BaseParser):
	# https://www.bigc.co.th/snacks-sweets.html
	def __init__(self):
		self.parser_id = 1
		self.subcats = {}
		self.brands = []
		self.static_url = 'https://static.bigc.co.th/'
		self.en = '?___store=en&___from_store=en&limit=100&mode=grid'
		self.img_dir = os.path.join(IMG_PATH, 'bigc')
		super().__init__()
		self.default_root = 'https://www.bigc.co.th/snacks-sweets.html'

	def get_soup(self, url, page=None):
		time.sleep(self.get_random_delay())
		url = url if url is not None else self.default_root
		if not self.en in url:
			url = url + self.en
		if page:
			url = url + '&p=' + str(page)
		headers = {
			'User-Agent': self.get_random_user_agent(),
			'Referer': url
		}
		# proxy = self.get_random_proxy()
		# if proxy:
		# 	proxies = {"http": proxy, "https": proxy}

		try:
			page = requests.get(url, headers=headers)
			# print(page.status_code, proxy)
			print(page.status_code)
			soup = BeautifulSoup(page.text, 'html.parser')
		except:
			print('FUCK UP! ', url)
			# self.test_proxilist()
			# self.get_soup(url, page)
		return soup

	def get_root(self, url=None):
		return url if url is not None else self.default_root

	def get_brands(self, url=None):
		soup = self.get_soup(url)
		brands_li = soup.find_all('a', {'class' : 'amshopby-attr'})
		for li in brands_li:
			brand_name = li.get_text().upper()
			if not brand_name in self.brands:
				self.brands.append(brand_name)

	def get_subcats(self, root_cat=None, parent=None):
		print('I COLLECT CATEGORIES NOW. {} - {}'.format(parent, root_cat))
		soup = self.get_soup(root_cat)
		if soup:
			# detect last page number of paginator
			last_num = 1
			try:
				last = soup.find('div',{'class':'pages-content'}).find('a',{'class':'last'})
				if last:
					last_num = int(last.get_text())
			except:
				pass
			subcats_li = soup.find_all('li', {'class': 'amshopby-cat'})
			for li in subcats_li:
				cat_url = li.a['href']
				cat_name = li.get_text()
				self.subcats[cat_name] = dict(url=cat_url, parent=parent, pages=last_num)
				if 'has-child' in str(li):
					self.get_subcats(root_cat=cat_url, parent=cat_name)
			self.get_brands()
			print(self.subcats)

	def extract_category_from_product(self, product_url=None):
		if product_url:
			page = requests.get(product_url+ '?___store=en&___from_store=en')
			html = page.text
			subsr = '"category": "'
			s = html.find(subsr)
			if s > 0:
				s1 = html.find('|\\')
				if s1 > 0:
					s_end = s + len(subsr)
					ln = s1 - s_end
					cat = html[s_end:s_end + ln]
					return cat

	def get_product(self, prod_link):
		product = None
		if not self.this_url_parsed_already(prod_link):
			soup = self.get_soup(prod_link)
			if soup:
				# cat_div = self.gettext(soup.find('div', {'class': 'breadcrumbs'}))
				sku = self.gettext(soup.find('span', {'class': 'sku-product'})).replace('SKU: ', '')
				name_div = soup.find(class_='product-name')
				if name_div:
					name = self.gettext(name_div.find(class_='h1'))
				if bool(name):
					if self.product_exists_in_db(sku, name):
						return None
					img_url = soup.find(id='amasty_zoom')['src']
					product = dict(
						img_url=img_url,
						name=name,
						# name_ru=self.translate(name),
						price=self.gettext(soup.find('span', {'class': 'price'})).replace('฿', ''),
						instock=self.gettext(soup.find('span', {'class': 'value'})).find('In stock') != -1,
						sku=sku,
						desc=self.gettext(soup.find('div', {'class': 'general_description'})),
						parser_id=self.parser_id,
						img_path=self.store_img_locally(img_url),
						brand=self.detect_brand(name),
						product_url=prod_link,
						category=self.extract_category_from_product(prod_link)
					)
				return product

	def get_category_products(self, cat_url=None, cat_name='', parent_cat='', page=1):
		soup = self.get_soup(cat_url, page=page)
		prods_ul = soup.find(class_='products-grid')
		prods_li = prods_ul.find_all('li')
		for li in prods_li:
			prod_link = li.a['href']
			product = self.get_product(prod_link)
			if product:
				if parent_cat is not None and parent_cat != cat_name:
					cat_string = '{}|{}'.format(parent_cat, cat_name)
				else:
					cat_string = cat_name
				product['category'] = cat_string
				self.save_product(product)
				print(product)

	def detect_brand(self, name=None):
		if name:
			i = name.upper().split(' ')
			if i[0] in self.brands:
				return i[0]
			else:
				two_word_brand = '{} {}'.format(i[0], i[1])
				if two_word_brand in self.brands:
					return two_word_brand

	def reparse_all_products_categories(self):
		products = self.session.query(Products).filter(Products.product_url != None).all()
		for i in products:
			url = i.product_url
			new_cat = self.extract_category_from_product(url)
			if new_cat:
				i.category = new_cat
				self.session.commit()
				print(new_cat, url)

	def translate_all_products_categories(self):
		translated = {}
		products = self.session.query(Products).filter(Products.category != None).all()
		for i in products:
			cat_en = i.category
			if cat_en in translated:
				cashed_trans = translated[cat_en]
				if cashed_trans:
					i.category_ru = cashed_trans
					self.session.commit()
					print(cashed_trans)
					continue

			cat_ru = self.translate(cat_en)
			if bool(cat_ru):
				translated[cat_en] = cat_ru
				i.category_ru = cat_ru
				self.session.commit()
				print('+', cat_ru)

	def run(self):
		# self.fetch_proxies()
		self.get_subcats()
		for name,data in self.subcats.items():
			for page in range(1, data['pages']):
				print('GETTING PAGE {} of {} / {}'.format(str(page), data['pages'] ,name))
				self.get_category_products(data['url'], cat_name=name, parent_cat=data['parent'], page=page)


if __name__ == '__main__':
	bc = Bigc()
	bc.run()
	# bc.reparse_all_products_categories()
	# bc.translate_all_products_categories()

	print('**** PARSING COMPLETED ****')
