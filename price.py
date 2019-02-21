#!/usr/bin/python
# -*- coding: utf-8 -*-
from jinja2 import Template
from sqlalchemy.orm import sessionmaker
from models import DB_ENGINE, Products
# from googletrans import Translator

# t = Translator()
sess = sessionmaker(DB_ENGINE)
session = sess()
price = open('template.html').read()
template = Template(price)


def create_category_price(categories=[]):
    for cat in categories:
        arr = cat.split("|")
        cat_name = arr[-1]
        products = session.query(Products).order_by(Products.name).filter(Products.category==cat).filter(Products.instock==True).limit(1000).all()
        if len(products)>20:
            print(cat)
            data = dict(cat_name=cat_name, products=products)
            out = template.render(data=data)
            with open("{}.html".format(cat.replace('/','_').replace('|','_')), "w") as html:
                print(out, file=html)

def get_categories_list():
    cats = session.query(Products.category).distinct(Products.category).filter(Products.instock == True).all()
    cat_list = []
    for i in cats:
        cat_list.append(i[0])
    return cat_list


if __name__ == '__main__':

    cats = get_categories_list()
    create_category_price(categories=cats)
