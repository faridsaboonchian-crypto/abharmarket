# make_qr.py
import qrcode
from PIL import Image, ImageDraw, ImageFont
import arabic_reshaper
from bidi.algorithm import get_display

def make_fancy_qr():
    link = "https://ble.ir/AbharMarket_bot"
    
    # ساخت QR با رنگ دلخواه (آبی تیره و سفید)
    qr = qrcode.QRCode(version=1, box_size=10, border=4)
    qr.add_data(link)
    qr.make(fit=True)
    
    # گرفتن عکس و تبدیل آن به حالت استاندارد RGB برای جلوگیری از خطای PIL
    img = qr.make_image(fill_color="darkblue", back_color="white").get_image()
    img = img.convert("RGB")
    
    # اضافه کردن فضای خالی زیر عکس برای نوشتن متن
    width, height = img.size
    new_height = height + 80
    new_img = Image.new('RGB', (width, new_height), 'white')
    new_img.paste(img, (0, 0))
    
    # تنظیمات نوشتن متن فارسی
    draw = ImageDraw.Draw(new_img)
    
    # استفاده از فونت ویندوز (Tahoma برای فارسی عالی است)
    try:
        font = ImageFont.truetype("Tahoma.ttf", 24)
    except:
        font = ImageFont.load_default()

    # متن شما
    text = "برای خرید آنلاین و سفارش سریع، این بارکد را اسکن کنید!"
    
    # اصلاح متن فارسی برای نمایش درست
    reshaped_text = arabic_reshaper.reshape(text)
    bidi_text = get_display(reshaped_text)
    
    # محاسبه وسط چین کردن متن
    text_width = draw.textlength(bidi_text, font=font)
    x = (width - text_width) / 2
    y = height + 20
    
    # کشیدن متن روی عکس
    draw.text((x, y), bidi_text, fill="black", font=font)
    
    # ذخیره نهایی
    new_img.save("AbharMarket_Fancy_QR.png")
    print("✅ بارکد جذاب با متن فارسی ساخته شد!")

if __name__ == '__main__':
    make_fancy_qr()