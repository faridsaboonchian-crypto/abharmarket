# database.py
from sqlalchemy import create_engine, Column, Integer, String, Float, ForeignKey, Boolean
from sqlalchemy.orm import declarative_base, relationship, sessionmaker

engine = create_engine('sqlite:///abhar_market.db', echo=False)
Base = declarative_base()

class Shop(Base):
    __tablename__ = 'shops'
    id = Column(Integer, primary_key=True)
    name = Column(String)
    owner_chat_id = Column(String, unique=True)
    is_active = Column(Boolean, default=True)

class Product(Base):
    __tablename__ = 'products'
    id = Column(Integer, primary_key=True)
    shop_id = Column(Integer, ForeignKey('shops.id'))
    name = Column(String)
    price = Column(Float)
    stock = Column(Integer, default=0)
    category = Column(String, nullable=True) # فیلد جدید برای دسته‌بندی
    description = Column(String, nullable=True)
    image_file_id = Column(String, nullable=True)

class Cart(Base):
    __tablename__ = 'carts'
    id = Column(Integer, primary_key=True)
    customer_eitaa_id = Column(String)
    product_id = Column(Integer, ForeignKey('products.id'))
    quantity = Column(Integer, default=1)

class Order(Base):
    __tablename__ = 'orders'
    id = Column(Integer, primary_key=True)
    shop_id = Column(Integer, default=1)
    customer_id = Column(String)
    phone = Column(String)
    address = Column(String)
    total_price = Column(Float, default=0)
    status = Column(String, default='pending')

class UserState(Base):
    __tablename__ = 'user_states'
    chat_id = Column(String, primary_key=True)
    state = Column(String, default='main')
    temp_data = Column(String, nullable=True)

Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)