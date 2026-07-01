# add_products.py
from database import Session, Product

print("در حال اضافه کردن محصولات نمونه...")
with Session() as session:
    # اول چک میکنیم آیا قبلا محصول اضافه شده یا نه
    if session.query(Product).count() == 0:
        p1 = Product(name="روغن مایع آفتاب (۱.۸ لیتر)", price=185000, stock=15)
        p2 = Product(name="برنج طارم (بسته ۵ کیلویی)", price=680000, stock=8)
        p3 = Product(name="شیر پگاه (۱ لیتری)", price=48000, stock=24)
        
        session.add_all([p1, p2, p3])
        session.commit()
        print("✅ ۳ محصول نمونه با موفقیت به دیتابیس اضافه شدند!")
    else:
        print("⚠️ محصولات قبلا اضافه شده‌اند.")