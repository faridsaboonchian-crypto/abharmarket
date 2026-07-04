import qrcode
from PIL import Image, ImageDraw, ImageFont
import arabic_reshaper
from bidi.algorithm import get_display
import os

def make_shop_standee(shop_id, shop_name):
    link = f"https://ble.ir/AbharMarket_bot?start=shop_{shop_id}"
    
    # ۱. ساخت QR Code
    qr = qrcode.QRCode(version=1, box_size=15, border=2)
    qr.add_data(link)
    qr.make(fit=True)
    qr_img = qr.make_image(fill_color="darkblue", back_color="white").get_image().convert("RGB")
    
    # ۲. ساخت بوم (Canvas) اصلی به سایز تقریبی A4
    width = 1000
    height = 1400
    canvas = Image.new('RGB', (width, height), 'white')
    
    # ۳. نوشتن متن‌ها با فونت فارسی (Tahoma)
    try:
        font_title = ImageFont.truetype("Tahoma.ttf", 60)
        font_shop = ImageFont.truetype("Tahoma.ttf", 80)
        font_desc = ImageFont.truetype("Tahoma.ttf", 40)
    except:
        font_title = ImageFont.load_default()
        font_shop = font_title
        font_desc = font_title

    draw = ImageDraw.Draw(canvas)
    
    # عنوان بالا
    title_text = "خرید آنلاین و سریع از ابهرمارکت"
    reshaped_title = get_display(arabic_reshaper.reshape(title_text))
    tw = draw.textlength(reshaped_title, font=font_title)
    draw.text(((width - tw) / 2, 100), reshaped_title, fill="darkblue", font=font_title)
    
    # نام فروشگاه
    shop_text = f"فروشگاه {shop_name}"
    reshaped_shop = get_display(arabic_reshaper.reshape(shop_text))
    sw = draw.textlength(reshaped_shop, font=font_shop)
    draw.text(((width - sw) / 2, 250), reshaped_shop, fill="black", font=font_shop)
    
    # چسباندن QR در وسط تصویر
    qr_x = (width - qr_img.width) // 2
    qr_y = 450
    canvas.paste(qr_img, (qr_x, qr_y))
    
    # توضیحات پایین
    desc1 = "دوربین گوشی خود را روی بارکد بگیرید"
    desc2 = "وارد کاتالوگ فروشگاه شوید، انتخاب کنید و سفارش بدهید."
    
    r_desc1 = get_display(arabic_reshaper.reshape(desc1))
    r_desc2 = get_display(arabic_reshaper.reshape(desc2))
    
    dw1 = draw.textlength(r_desc1, font=font_desc)
    dw2 = draw.textlength(r_desc2, font=font_desc)
    
    draw.text(((width - dw1) / 2, qr_y + qr_img.height + 50), r_desc1, fill="gray", font=font_desc)
    draw.text(((width - dw2) / 2, qr_y + qr_img.height + 120), r_desc2, fill="gray", font=font_desc)
    
    # ذخیره نهایی
    file_name = f"Standee_{shop_name}.png"
    canvas.save(file_name)
    print(f"✅ استند حرفه‌ای برای '{shop_name}' ساخته شد: {file_name}")

# مثال برای تست:
# وقتی مغازه‌ای ثبت کردید، نام و آیدیش را اینجا بزنید و اجرا کنید
make_shop_standee(1563770441, "فروشگاه رفاه شعبه طالقانی")