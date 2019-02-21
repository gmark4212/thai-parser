#!/usr/bin/python
# -*- coding: utf-8 -*-

import os
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, String, Float, Boolean

DB_FOLDER_PATH = os.path.dirname(os.path.relpath(__file__))
DB_PATH = os.path.join(DB_FOLDER_PATH, 'base.db')
IMG_PATH = os.path.join(DB_FOLDER_PATH, 'img')
DB_ENGINE = create_engine('sqlite:///{}'.format(DB_PATH), connect_args={'check_same_thread': False}, echo=False)

Base = declarative_base()


class Products(Base):
    __tablename__ = 'product'
    pid = Column(Integer, primary_key=True)
    sku = Column(String(25), nullable=True)
    name = Column(String(250), nullable=False)
    name_ru = Column(String(250), nullable=True)
    brand = Column(String(100), nullable=True)
    img_url = Column(String(250), nullable=False)
    img_path = Column(String(250), nullable=False)
    price = Column(Float, nullable=True)
    instock = Column(Boolean, default=False)
    category = Column(String(250), nullable=True)
    category_ru = Column(String(250), nullable=True)
    parser_id = Column(Integer, nullable=False)
    desc = Column(String(250), nullable=True)
    product_url = Column(String(250), nullable=True)

    def __init__(self, **kwargs):
        for key in kwargs:
            if hasattr(self, key):
                setattr(self, key, kwargs[key])


Base.metadata.create_all(DB_ENGINE)
