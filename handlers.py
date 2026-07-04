# handlers.py
from database import Session, Product, Cart, Order, UserState, Shop
from bot_api import BotAPI
from config import BOT_TOKEN
from sqlalchemy.exc import IntegrityError
import time

bot = BotAPI(BOT_TOKEN)
ADMIN_ID = "1563770441"

def convert_to_english_digits(text):
    if not text: return text
    persian = '۰۱۲۳۴۵۶۷۸۹'
    arabic = '٠١٢٣٤٥٦٧٨٩'
    for i, ch in enumerate(persian):
        text = text.replace(ch, str(i))
    for i, ch in enumerate(arabic):
        text = text.replace(ch, str(i))
    return text

def is_button(text):
    buttons = ['➕ ثبت فروشگاه جدید', '📊 آمار سیستم', '🏪 لیست فروشگاه‌ها', '🗑 حذف فروشگاه', '🔙 بازگشت', '➕ افزودن محصول جدید', '📦 مدیریت محصولات', '🔍 جستجوی محصول', '🔙 بازگشت به منوی مشتری', '🛒 مشاهده محصولات', '🛍 سبد خرید', '👤 پشتیبانی']
    return text in buttons

def format_price(price):
    return f"{int(price):,}"

def main_keyboard():
    return {"keyboard": [["🛒 مشاهده محصولات"], ["🛍 سبد خرید", "👤 پشتیبانی"]], "resize_keyboard": True}

def vendor_keyboard():
    return {"keyboard": [["➕ افزودن محصول جدید"], ["📦 مدیریت محصولات"], ["🔙 بازگشت به منوی مشتری"]], "resize_keyboard": True}

def admin_keyboard():
    return {"keyboard": [["➕ ثبت فروشگاه جدید", "🗑 حذف فروشگاه"], ["📊 آمار سیستم", "🏪 لیست فروشگاه‌ها"], ["🔙 بازگشت"]], "resize_keyboard": True}

def reset_state_to_main(chat_id):
    with Session() as session:
        state = session.query(UserState).filter_by(chat_id=str(chat_id)).first()
        if not state:
            state = UserState(chat_id=str(chat_id))
            session.add(state)
        state.state = 'main'
        state.temp_data = None
        session.commit()
    start_bot(chat_id)

def start_bot(chat_id, deep_link_data=None):
    if deep_link_data and deep_link_data == 'myid':
        bot.send_message(chat_id, f"🔍 آیدی عددی شما در بله:\n{chat_id}\n\nاین عدد را به ادمین سیستم بدهید تا فروشگاه شما را ثبت کند.")
        return

    with Session() as session:
        state = session.query(UserState).filter_by(chat_id=str(chat_id)).first()
        if not state:
            state = UserState(chat_id=str(chat_id))
            session.add(state)
        state.state = 'main'
        session.commit()
    
    if deep_link_data and deep_link_data.startswith('shop_'):
        shop_id = int(deep_link_data.replace('shop_', ''))
        with Session() as session:
            shop = session.query(Shop).get(shop_id)
            if shop:
                msg = f"🎉 به فروشگاه '{shop.name}' خوش آمدید!\n\n"
                msg += "محصولات این فروشگاه در زیر نمایش داده شد. شما می‌توانید برای مقایسه قیمت‌ها، از دکمه '🛒 مشاهده محصولات' در منوی پایین، سایر فروشگاه‌های ابهر را نیز مشاهده کنید."
                bot.send_message(chat_id, msg, main_keyboard())
                show_shop_products(chat_id, shop_id)
                return

    bot.send_message(chat_id, "به ربات فروشگاهی ابهر مارکت خوش آمدید!\nبرای شروع، روی دکمه‌های زیر کلیک کنید.", main_keyboard())

def show_admin_panel(chat_id):
    if str(chat_id) != ADMIN_ID: return
    with Session() as session:
        shops_count = session.query(Shop).count()
        products_count = session.query(Product).count()
        orders_count = session.query(Order).count()
    msg = "👑 **پنل مدیریت کل**\n\n"
    msg += f"🏪 تعداد فروشگاه‌ها: {shops_count}\n"
    msg += f"📦 تعداد کل محصولات: {products_count}\n"
    msg += f"🛒 تعداد کل سفارشات: {orders_count}\n"
    bot.send_message(chat_id, msg, admin_keyboard())

def list_shops(chat_id):
    if str(chat_id) != ADMIN_ID: return
    with Session() as session:
        shops = session.query(Shop).all()
        if not shops:
            bot.send_message(chat_id, "هنوز هیچ فروشگاهی ثبت نشده است.")
            return
        msg = "🏪 **لیست فروشگاه‌ها:**\n\n"
        for s in shops:
            status = "✅ فعال" if s.is_active else "❌ غیرفعال"
            msg += f"ID: {s.id} | {s.name} | آیدی مالک: {s.owner_chat_id} | {status}\n"
        bot.send_message(chat_id, msg)

def list_shops_for_delete(chat_id):
    if str(chat_id) != ADMIN_ID: return
    with Session() as session:
        shops = session.query(Shop).all()
        if not shops:
            bot.send_message(chat_id, "هیچ فروشگاهی برای حذف وجود ندارد.")
            return
        buttons = []
        for s in shops:
            buttons.append([{"text": f"🗑 {s.name}", "callback_data": f"dels_{s.id}"}])
        keyboard = {"inline_keyboard": buttons}
        bot.send_message(chat_id, "لطفاً فروشگاهی که می‌خواهید حذف کنید را انتخاب کنید:", keyboard)

def delete_shop(chat_id, shop_id):
    if str(chat_id) != ADMIN_ID: return
    with Session() as session:
        shop = session.query(Shop).get(shop_id)
        if shop:
            session.query(Product).filter_by(shop_id=shop_id).delete()
            session.delete(shop)
            session.commit()
            bot.send_message(chat_id, f"✅ فروشگاه و محصولات آن حذف شد.", admin_keyboard())

def process_admin_step(chat_id, text):
    if str(chat_id) != ADMIN_ID: return
    text = convert_to_english_digits(text)
    with Session() as session:
        state = session.query(UserState).filter_by(chat_id=str(chat_id)).first()
        if not state:
            state = UserState(chat_id=str(chat_id), state='main')
            session.add(state)
            session.commit()

        if text == '/admin' or text == '📊 آمار سیستم': show_admin_panel(chat_id); return
        elif text == '🏪 لیست فروشگاه‌ها': list_shops(chat_id); return
        elif text == '🗑 حذف فروشگاه': list_shops_for_delete(chat_id); return

        if text == '➕ ثبت فروشگاه جدید' and state.state == 'main':
            state.state = 'admin_shop_name'
            session.commit()
            bot.send_message(chat_id, "۱. لطفاً **نام فروشگاه** را وارد کنید:")
            return

        if state.state == 'admin_shop_name':
            if is_button(text):
                bot.send_message(chat_id, "⚠️ لطفاً یک نام معتبر تایپ کنید، نه دکمه را:")
                return
            state.temp_data = f"name:{text}"
            state.state = 'admin_shop_owner'
            session.commit()
            bot.send_message(chat_id, "۲. لطفاً **آیدی عددی مغازه‌دار** در بله را وارد کنید:")
            return

        if state.state == 'admin_shop_owner':
            if is_button(text):
                bot.send_message(chat_id, "⚠️ لطفاً آیدی عددی معتبر وارد کنید:")
                return
            try:
                shop_name = state.temp_data.split(":", 1)[1]
                new_shop = Shop(name=shop_name, owner_chat_id=text, is_active=True)
                session.add(new_shop)
                state.state = 'main'
                state.temp_data = None
                session.commit()
                bot.send_message(chat_id, f"✅ فروشگاه '{new_shop.name}' ثبت شد!", admin_keyboard())
            except IntegrityError:
                session.rollback()
                bot.send_message(chat_id, "⚠️ این آیدی قبلاً ثبت شده است!", admin_keyboard())
            return

def show_shops_menu(chat_id):
    with Session() as session:
        shops = session.query(Shop).filter_by(is_active=True).all()
        if not shops:
            bot.send_message(chat_id, "هنوز فروشگاهی در سیستم ثبت نشده است.")
            return
        buttons = []
        for s in shops:
            buttons.append([{"text": f"🏪 {s.name}", "callback_data": f"shop_{s.id}"}])
        keyboard = {"inline_keyboard": buttons}
        bot.send_message(chat_id, "🏦 لطفاً فروشگاه مورد نظر خود را انتخاب کنید:", keyboard)

def show_shop_products(chat_id, shop_id):
    with Session() as session:
        shop = session.query(Shop).get(shop_id)
        if not shop: return
        products = session.query(Product).filter_by(shop_id=shop_id).all()
        if not products:
            bot.send_message(chat_id, f"فروشگاه '{shop.name}' هنوز محصولی ثبت نکرده است.")
            return
        categories = []
        for p in products:
            cat = p.category if p.category and p.category not in ['None', 'empty_desc', 'سایر'] else "سایر"
            if cat not in categories: categories.append(cat)
        buttons = []
        # اضافه شدن دکمه جستجو در بالای لیست برای مشتری
        buttons.append([{"text": "🔍 جستجوی محصول", "callback_data": f"csearch_{shop_id}"}])
        for cat in categories:
            # استفاده از پیشوند c_ برای صفحه‌بندی و شروع از صفحه 1
            buttons.append([{"text": f"🏷 {cat}", "callback_data": f"c_{shop_id}_{cat}_1"}])
        keyboard = {"inline_keyboard": buttons}
        bot.send_message(chat_id, f"🏦 فروشگاه '{shop.name}'\nلطفاً دسته‌بندی را انتخاب کنید یا برای پیدا کردن سریع محصول، روی جستجو بزنید:", keyboard)

def start_customer_search(chat_id, shop_id):
    with Session() as session:
        state = session.query(UserState).filter_by(chat_id=str(chat_id)).first()
        if not state:
            state = UserState(chat_id=str(chat_id))
            session.add(state)
        state.state = 'customer_search_prod'
        state.temp_data = str(shop_id)
        session.commit()
    bot.send_message(chat_id, "🔍 لطفاً **بخشی از نام محصول** که به دنبال آن هستید را ارسال کنید (مثلاً: روغن اویلا):")

def process_customer_search(chat_id, user_id, text):
    text = convert_to_english_digits(text)
    # اعتبارسنجی متن جستجو
    if not text or len(text) < 2 or len(text) > 50:
        bot.send_message(chat_id, "⚠️ عبارت جستجو نامعتبر است. لطفاً بین ۲ تا ۵۰ کاراکتر وارد کنید:")
        return

    with Session() as session:
        state = session.query(UserState).filter_by(chat_id=str(chat_id)).first()
        if not state or not state.temp_data:
            return
        
        shop_id = int(state.temp_data)
        search_term = f"%{text}%"
        
        # محدود کردن به 10 نتیجه اول برای جلوگیری از اسپم و مسدودی ربات
        products = session.query(Product).filter(
            Product.shop_id == shop_id, 
            Product.name.ilike(search_term)
        ).limit(10).all()
        
        if not products:
            bot.send_message(chat_id, "⚠️ محصولی با این نام در این فروشگاه یافت نشد. لطفاً کلمه دیگری را امتحان کنید:")
            return

        shop = session.query(Shop).get(shop_id)
        bot.send_message(chat_id, f"✅ نتایج جستجو در '{shop.name}':")
        
        for p in products:
            prod_text = f"📦 {p.name}\n💰 قیمت: {format_price(p.price)} تومان\nموجودی: {p.stock} عدد"
            if p.description and p.description not in ['None', 'empty_desc']:
                prod_text += f"\n📝 توضیحات: {p.description}"
            keyboard = {"inline_keyboard": [[{"text": "➕ افزودن به سبد", "callback_data": f"add_{p.id}"}]]}
            if p.image_file_id:
                try:
                    bot.send_photo(chat_id, p.image_file_id, prod_text, keyboard)
                    time.sleep(0.5) 
                except Exception as e:
                    print(f"Error sending photo: {e}")
            else:
                bot.send_message(chat_id, prod_text, keyboard)
                time.sleep(0.2)
        
        # ---------------- بخش جدید: دکمه بازگشت به لیست محصولات ----------------
        # استفاده از کال‌بک shop_{shop_id} که قبلا در main.py تعریف شده تا لیست دسته‌بندی‌ها بیاید
        back_keyboard = {
            "inline_keyboard": [
                [{"text": "🔙 بازگشت به لیست محصولات", "callback_data": f"shop_{shop_id}"}]
            ]
        }
        bot.send_message(chat_id, "اگر محصول مورد نظر شما در لیست بالا نبود، می‌توانید به لیست دسته‌بندی‌ها برگردید:", back_keyboard)
        # --------------------------------------------------------------------
        
        # ریست کردن State به منوی اصلی
        state.state = 'main'
        state.temp_data = None
        session.commit()


def show_category_products(chat_id, shop_id, category, page=1):
    items_per_page = 5
    with Session() as session:
        if category == "سایر":
            products = session.query(Product).filter(
                Product.shop_id == shop_id,
                (Product.category == None) | (Product.category == 'None') | (Product.category == 'empty_desc') | (Product.category == 'سایر')
            ).all()
        else:
            products = session.query(Product).filter_by(shop_id=shop_id, category=category).all()

        if not products:
            bot.send_message(chat_id, "محصولی در این دسته یافت نشد.")
            return
            
        total_items = len(products)
        start_idx = (page - 1) * items_per_page
        end_idx = start_idx + items_per_page
        current_products = products[start_idx:end_idx]
        
        bot.send_message(chat_id, f"🛍️ دسته‌بندی: {category} (صفحه {page})")
        
        for p in current_products:
            text = f"📦 {p.name}\n💰 قیمت: {format_price(p.price)} تومان\nموجودی: {p.stock} عدد"
            if p.description and p.description not in ['None', 'empty_desc']:
                text += f"\n📝 توضیحات: {p.description}"
            keyboard = {"inline_keyboard": [[{"text": "➕ افزودن به سبد", "callback_data": f"add_{p.id}"}]]}
            if p.image_file_id:
                try:
                    bot.send_photo(chat_id, p.image_file_id, text, keyboard)
                    time.sleep(0.5) 
                except Exception as e:
                    print(f"Error sending photo: {e}")
            else:
                bot.send_message(chat_id, text, keyboard)
                time.sleep(0.2)
                
        # ساخت دکمه‌های صفحه‌بندی و بازگشت به دسته‌بندی‌ها
        pagination_buttons = []
        if page > 1:
            pagination_buttons.append({"text": "⬅️ صفحه قبل", "callback_data": f"c_{shop_id}_{category}_{page-1}"})
        
        # دکمه بازگشت به منوی دسته‌بندی‌ها برای جلوگیری از اسکرول
        pagination_buttons.append({"text": "🔙 دسته‌بندی‌ها", "callback_data": f"shop_{shop_id}"})
        
        if end_idx < total_items:
            pagination_buttons.append({"text": "صفحه بعد ➡️", "callback_data": f"c_{shop_id}_{category}_{page+1}"})
            
        keyboard = {"inline_keyboard": [pagination_buttons]}
        bot.send_message(chat_id, "برای مشاهده ادامه محصولات یا تغییر دسته، از دکمه‌های زیر استفاده کنید:", keyboard)

def add_to_cart(chat_id, user_id, product_id):
    with Session() as session:
        state = session.query(UserState).filter_by(chat_id=str(chat_id)).first()
        if not state:
            state = UserState(chat_id=str(chat_id))
            session.add(state)
        state.state = 'adding_quantity'
        state.temp_data = str(product_id)
        session.commit()
    bot.send_message(chat_id, "لطفاً **تعداد** مورد نظر خود را برای این محصول به عدد وارد کنید (مثلاً ۲):")

def process_quantity_step(chat_id, user_id, text):
    text = convert_to_english_digits(text)
    if not text.isdigit() or int(text) <= 0:
        bot.send_message(chat_id, "⚠️ لطفاً یک عدد معتبر و بزرگتر از صفر وارد کنید:")
        return
        
    quantity = int(text)
    with Session() as session:
        state = session.query(UserState).filter_by(chat_id=str(chat_id)).first()
        if not state: return
            
        try: prod_id = int(state.temp_data)
        except (ValueError, TypeError):
            bot.send_message(chat_id, "⚠️ خطا در شناسایی محصول.", main_keyboard())
            state.state = 'main'; state.temp_data = None; session.commit(); return
            
        product = session.query(Product).get(prod_id)
        if not product:
            bot.send_message(chat_id, "⚠️ محصول یافت نشد.")
            state.state = 'main'; session.commit(); return
            
        if product.stock < quantity:
            bot.send_message(chat_id, f"⚠️ موجودی کافی نیست. حداکثر {product.stock} عدد موجود است.")
            state.state = 'main'; session.commit(); return
            
        cart_item = session.query(Cart).filter_by(customer_eitaa_id=str(user_id), product_id=prod_id).first()
        if cart_item:
            cart_item.quantity += quantity
        else:
            cart_item = Cart(customer_eitaa_id=str(user_id), product_id=prod_id, quantity=quantity)
            session.add(cart_item)
            
        state.state = 'main'
        state.temp_data = None
        session.commit()
        product_name = product.name
        
    bot.send_message(chat_id, f"✅ {quantity} عدد از '{product_name}' به سبد شما اضافه شد.")

def show_cart(chat_id, user_id):
    with Session() as session:
        cart_items = session.query(Cart).filter_by(customer_eitaa_id=str(user_id)).all()
        if not cart_items:
            bot.send_message(chat_id, "🛍 سبد خرید شما خالی است.")
            return
            
        msg = "🛍 **فاکتور خرید شما:**\n\n"
        total_price = 0
        keyboard_buttons = []
        
        for item in cart_items:
            p = session.query(Product).get(item.product_id)
            if not p: continue
            item_total = p.price * item.quantity
            total_price += item_total
            msg += f"▫️ {p.name}\n   {item.quantity} عدد × {format_price(p.price)} = {format_price(item_total)} تومان\n"
            keyboard_buttons.append([{"text": f"❌ حذف: {p.name}", "callback_data": f"rmcart_{item.id}"}])
            
        msg += f"\n➖➖➖➖➖➖➖➖\n💰 **مجموع کل: {format_price(total_price)} تومان**"
        keyboard_buttons.append([{"text": "🗑 خالی کردن کل سبد", "callback_data": "clearcart"}])
        keyboard_buttons.append([{"text": "✅ نهایی کردن خرید", "callback_data": "checkout"}])
        
        keyboard = {"inline_keyboard": keyboard_buttons}
        bot.send_message(chat_id, msg, keyboard)

def remove_cart_item(chat_id, user_id, cart_id):
    with Session() as session:
        cart_item = session.query(Cart).filter_by(id=cart_id, customer_eitaa_id=str(user_id)).first()
        if cart_item:
            session.delete(cart_item)
            session.commit()
            bot.send_message(chat_id, "✅ محصول از سبد شما حذف شد.")
        else:
            bot.send_message(chat_id, "⚠️ این محصول در سبد شما یافت نشد.")
    show_cart(chat_id, user_id)

def clear_cart(chat_id, user_id):
    with Session() as session:
        session.query(Cart).filter_by(customer_eitaa_id=str(user_id)).delete()
        session.commit()
        bot.send_message(chat_id, "🗑 سبد خرید شما کاملاً خالی شد.")

def start_checkout(chat_id, user_id):
    with Session() as session:
        if session.query(Cart).filter_by(customer_eitaa_id=str(user_id)).count() == 0:
            bot.send_message(chat_id, "سبد خرید شما خالی است!")
            return
        state = session.query(UserState).filter_by(chat_id=str(chat_id)).first()
        if not state:
            state = UserState(chat_id=str(chat_id))
            session.add(state)
        state.state = 'waiting_phone'
        session.commit()
        keyboard = {"keyboard": [["🔙 بازگشت"]], "resize_keyboard": True}
        bot.send_message(chat_id, "🙏 لطفاً **شماره موبایل** خود را وارد کنید:", keyboard)

def process_checkout_step(chat_id, user_id, text):
    text = convert_to_english_digits(text)
    with Session() as session:
        state = session.query(UserState).filter_by(chat_id=str(chat_id)).first()
        if not state: return

        if state.state == 'waiting_phone':
            # اعتبارسنجی شماره تلفن (حداکثر 15 کاراکتر و فقط عدد)
            if not text.isdigit() or len(text) > 15 or len(text) < 4:
                bot.send_message(chat_id, "⚠️ شماره نامعتبر است. لطفاً فقط عدد (بدون فاصله) وارد کنید:")
                return
            state.temp_data = f"phone|||{text}"
            state.state = 'waiting_address'
            session.commit()
            bot.send_message(chat_id, "✅ شماره ثبت شد.\n📍 حالا **آدرس کامل** را وارد کنید:")
            return

        elif state.state == 'waiting_address':
            # اعتبارسنجی آدرس (حداکثر 300 کاراکتر)
            if len(text) > 300:
                bot.send_message(chat_id, "⚠️ آدرس شما بسیار طولانی است! لطفاً آدرس را به صورت خلاصه‌تر (کمتر از ۳۰۰ کاراکتر) وارد کنید:")
                return
            data_str = state.temp_data + f"|||address|||{text}"
            data_dict = {}
            parts = data_str.split("|||")
            for i in range(0, len(parts)-1, 2):
                data_dict[parts[i]] = parts[i+1]
            phone = data_dict.get("phone", "")
            address = data_dict.get("address", "")

            cart_items = session.query(Cart).filter_by(customer_eitaa_id=str(user_id)).all()
            if not cart_items:
                bot.send_message(chat_id, "سبد خرید شما خالی است!", main_keyboard())
                state.state = 'main'; session.commit(); return

            total_price = 0
            items_text_customer = ""
            shop_orders = {}

            for item in cart_items:
                p = session.query(Product).get(item.product_id)
                if not p: continue
                item_total = p.price * item.quantity
                total_price += item_total
                items_text_customer += f"▫️ {p.name} ({item.quantity} عدد) - {format_price(item_total)} تومان\n"

                if p.shop_id not in shop_orders:
                    shop = session.query(Shop).get(p.shop_id)
                    shop_orders[p.shop_id] = {"items_text": "", "total": 0, "owner_id": shop.owner_chat_id, "shop_name": shop.name}
                shop_orders[p.shop_id]["items_text"] += f"▫️ {p.name} ({item.quantity} عدد) - {format_price(item_total)} تومان\n"
                shop_orders[p.shop_id]["total"] += item_total

            new_order = Order(customer_id=str(user_id), phone=phone, address=address, total_price=total_price)
            session.add(new_order)
            session.flush()

            for item in cart_items:
                session.delete(item)

            state.state = 'main'
            state.temp_data = None
            session.commit()

            customer_msg = f"🎉 سفارش شما با کد {new_order.id} ثبت شد!\n\n📦 **اقلام سفارش:**\n{items_text_customer}\n💰 **مبلغ کل: {format_price(total_price)} تومان**\n\n📍 آدرس: {new_order.address}\n📞 تلفن: {new_order.phone}\n\nسفارش شما در انتظار تایید فروشنده است."
            bot.send_message(chat_id, customer_msg, main_keyboard())

            for shop_id, data in shop_orders.items():
                vendor_msg = f"🔔 سفارش جدید برای فروشگاه شما ({data['shop_name']})!\n\nکد سفارش: {new_order.id}\n📞 شماره مشتری: {new_order.phone}\n📍 آدرس: {new_order.address}\n\n📦 **اقلام این فروشگاه:**\n{data['items_text']}\n💰 مبلغ قابل دریافت شما: {format_price(data['total'])} تومان"
                accept_keyboard = {"inline_keyboard": [[{"text": "✅ تایید سفارش و ارسال", "callback_data": f"accept_{new_order.id}"}]]}
                try: bot.send_message(str(data['owner_id']), vendor_msg, accept_keyboard)
                except Exception as e: print(f"⚠️ خطا در ارسال به مغازه‌دار: {e}")

            admin_msg = f"🔔 سفارش جدید در سیستم!\n\nکد: {new_order.id}\n📞 شماره: {new_order.phone}\n📍 آدرس: {new_order.address}\n\n📦 **کل اقلام:**\n{items_text_customer}\n💰 مبلغ کل: {format_price(total_price)} تومان"
            try: bot.send_message(ADMIN_ID, admin_msg)
            except: pass
            return

def process_vendor_step(chat_id, text, photo=None):
    text = convert_to_english_digits(text)
    with Session() as session:
        state = session.query(UserState).filter_by(chat_id=str(chat_id)).first()
        if not state: return

        # ---------------- بخش جدید: مدیریت جستجوی محصول ----------------
        if state.state == 'vendor_search_prod':
            if is_button(text) or not text or len(text) < 2 or len(text) > 50:
                bot.send_message(chat_id, "⚠️ عبارت جستجو نامعتبر است. لطفاً بین ۲ تا ۵۰ کاراکتر وارد کنید:")
                return
            
            shops = session.query(Shop).filter_by(is_active=True).all()
            shop = None
            for s in shops:
                if convert_to_english_digits(s.owner_chat_id) == str(chat_id):
                    shop = s
                    break
            if not shop: return

            # جستجوی سیلابیک در دیتابیس (ilike)
            search_term = f"%{text}%"
            products = session.query(Product).filter(
                Product.shop_id == shop.id, 
                Product.name.ilike(search_term)
            ).all()
            
            if not products:
                bot.send_message(chat_id, "⚠️ محصولی با این نام یافت نشد. لطفاً کلمه دیگری را امتحان کنید:")
                return
                
            buttons = []
            for p in products:
                buttons.append([{"text": f"📦 {p.name} (قیمت: {format_price(p.price)} - موجودی: {p.stock})", "callback_data": f"editvp_{p.id}"}])
            
            buttons.append([{"text": "🔙 بازگشت به دسته‌بندی‌ها", "callback_data": "manage_cats"}])
            keyboard = {"inline_keyboard": buttons}
            bot.send_message(chat_id, f"✅ {len(products)} محصول یافت شد. لطفاً محصول مورد نظر را برای ویرایش انتخاب کنید:", keyboard)
            
            # ریست کردن State به منوی فروشندگی
            state.state = 'vendor_menu'
            state.temp_data = None
            session.commit()
            return
        # ----------------------------------------------------------------

        if text == '➕ افزودن محصول جدید' and state.state == 'vendor_menu':
            state.state = 'vendor_name'; session.commit()
            bot.send_message(chat_id, "۱. **نام محصول** را وارد کنید:"); return

        if text == '📦 مدیریت محصولات' and state.state == 'vendor_menu':
            list_vendor_products(chat_id); return

        if state.state == 'vendor_edit_name':
            if is_button(text) or not text or len(text) < 2 or len(text) > 100:
                bot.send_message(chat_id, "⚠️ نام نامعتبر است. لطفاً بین ۲ تا ۱۰۰ کاراکتر وارد کنید:"); return
            try: prod_id = int(state.temp_data)
            except (ValueError, TypeError):
                bot.send_message(chat_id, "⚠️ خطا در شناسایی محصول.", vendor_keyboard())
                state.state = 'vendor_menu'; state.temp_data = None; session.commit(); return

            p = session.query(Product).get(prod_id)
            if p:
                p.name = text; session.commit()
                bot.send_message(chat_id, "✅ نام محصول با موفقیت بروزرسانی شد.", vendor_keyboard())
            else: bot.send_message(chat_id, "⚠️ محصول یافت نشد.")
            state.state = 'vendor_menu'; state.temp_data = None; session.commit(); return

        if state.state == 'vendor_edit_price':
            if not text.isdigit() or len(text) > 12:
                bot.send_message(chat_id, "⚠️ قیمت باید فقط عدد و معقول باشد. دوباره وارد کنید:"); return
            try: prod_id = int(state.temp_data)
            except (ValueError, TypeError):
                bot.send_message(chat_id, "⚠️ خطا در شناسایی محصول.", vendor_keyboard())
                state.state = 'vendor_menu'; state.temp_data = None; session.commit(); return

            p = session.query(Product).get(prod_id)
            if p:
                p.price = float(text); session.commit()
                bot.send_message(chat_id, "✅ قیمت با موفقیت بروزرسانی شد.", vendor_keyboard())
            else: bot.send_message(chat_id, "⚠️ محصول یافت نشد.")
            state.state = 'vendor_menu'; state.temp_data = None; session.commit(); return

        elif state.state == 'vendor_edit_stock':
            if not text.isdigit() or len(text) > 6:
                bot.send_message(chat_id, "⚠️ موجودی باید فقط عدد باشد. دوباره وارد کنید:"); return
            try: prod_id = int(state.temp_data)
            except (ValueError, TypeError):
                bot.send_message(chat_id, "⚠️ خطا در شناسایی محصول.", vendor_keyboard())
                state.state = 'vendor_menu'; state.temp_data = None; session.commit(); return

            p = session.query(Product).get(prod_id)
            if p:
                p.stock = int(text); session.commit()
                bot.send_message(chat_id, "✅ موجودی با موفقیت بروزرسانی شد.", vendor_keyboard())
            else: bot.send_message(chat_id, "⚠️ محصول یافت نشد.")
            state.state = 'vendor_menu'; state.temp_data = None; session.commit(); return

        if state.state == 'vendor_name':
            if is_button(text) or not text or len(text) < 2 or len(text) > 100:
                bot.send_message(chat_id, "⚠️ نام نامعتبر است. لطفاً بین ۲ تا ۱۰۰ کاراکتر تایپ کنید:"); return
            state.temp_data = f"name:{text}"; state.state = 'vendor_price'; session.commit()
            bot.send_message(chat_id, "۲. **قیمت** را به تومان وارد کنید (فقط عدد):"); return

        elif state.state == 'vendor_price':
            if not text.isdigit() or len(text) > 12:
                bot.send_message(chat_id, "⚠️ قیمت باید فقط عدد باشد:"); return
            state.temp_data += f"|price:{text}"; state.state = 'vendor_stock'; session.commit()
            bot.send_message(chat_id, "۳. **موجودی** را وارد کنید (فقط عدد):"); return

        elif state.state == 'vendor_stock':
            if not text.isdigit() or len(text) > 6:
                bot.send_message(chat_id, "⚠️ موجودی باید عدد باشد:"); return
            state.temp_data += f"|stock:{text}"; state.state = 'vendor_cat'; session.commit()
            bot.send_message(chat_id, "۴. **دسته‌بندی محصول** را وارد کنید (مثلاً: روغن، برنج، شوینده):"); return

        elif state.state == 'vendor_cat':
            if is_button(text) or text == 'ندارد' or len(text) > 50:
                bot.send_message(chat_id, "⚠️ دسته‌بندی نامعتبر است. لطفاً کوتاه و معتبر وارد کنید:"); return
            state.temp_data += f"|cat:{text}"; state.state = 'vendor_desc'; session.commit()
            bot.send_message(chat_id, "۵. **توضیحات** را وارد کنید (اگر ندارد بنویسید 'ندارد'):"); return

        elif state.state == 'vendor_desc':
            if len(text) > 500:
                bot.send_message(chat_id, "⚠️ توضیحات بسیار طولانی است. لطفاً کمتر از ۵۰۰ کاراکتر بنویسید:"); return
            desc_text = text if text != 'ندارد' else 'empty_desc'
            state.temp_data += f"|desc:{desc_text}"; state.state = 'vendor_photo'; session.commit()
            bot.send_message(chat_id, "۶. عکس محصول را ارسال کنید."); return

        elif state.state == 'vendor_photo':
            if not photo:
                bot.send_message(chat_id, "⚠️ لطفاً یک عکس ارسال کنید."); return
            file_id = photo[-1]['file_id'] if isinstance(photo, list) else photo['file_id']
            data_str = state.temp_data
            data_dict = {p.split(":", 1)[0]: p.split(":", 1)[1] for p in data_str.split("|")}
            
            shops = session.query(Shop).all()
            shop = None
            for s in shops:
                if convert_to_english_digits(s.owner_chat_id) == str(chat_id):
                    shop = s
                    break

            final_desc = data_dict.get("desc")
            if final_desc == 'empty_desc': final_desc = None

            new_product = Product(
                name=data_dict.get("name"),
                price=float(data_dict.get("price")),
                stock=int(data_dict.get("stock")),
                category=data_dict.get("cat"),
                description=final_desc,
                image_file_id=file_id,
                shop_id=shop.id
            )
            session.add(new_product)
            state.state = 'vendor_menu'; state.temp_data = None; session.commit()
            bot.send_message(chat_id, f"✅ محصول '{new_product.name}' ثبت شد!", vendor_keyboard())
            return

def start_vendor_panel(chat_id):
    shop_name = None
    with Session() as session:
        shops = session.query(Shop).filter_by(is_active=True).all()
        valid_shop = None
        for s in shops:
            if convert_to_english_digits(s.owner_chat_id) == str(chat_id):
                valid_shop = s
                break
        if not valid_shop:
            bot.send_message(chat_id, "⚠️ دسترسی شما مسدود است یا فروشگاهی برای شما ثبت نشده است.")
            return
        shop_name = valid_shop.name
        state = session.query(UserState).filter_by(chat_id=str(chat_id)).first()
        if not state:
            state = UserState(chat_id=str(chat_id))
            session.add(state)
        state.state = 'vendor_menu'
        session.commit()
    bot.send_message(chat_id, f"🏭 پنل فروشندگی:\nفروشگاه: {shop_name}", vendor_keyboard())

def list_vendor_products(chat_id):
    with Session() as session:
        shops = session.query(Shop).filter_by(is_active=True).all()
        shop = None
        for s in shops:
            if convert_to_english_digits(s.owner_chat_id) == str(chat_id):
                shop = s
                break
        if not shop: return
        
        products = session.query(Product).filter_by(shop_id=shop.id).all()
        if not products:
            bot.send_message(chat_id, "شما هنوز محصولی ثبت نکرده‌اید.")
            return
            
        # استخراج دسته‌بندی‌های یکتا
        categories = []
        for p in products:
            cat = p.category if p.category and p.category not in ['None', 'empty_desc', 'سایر'] else "سایر"
            if cat not in categories: categories.append(cat)
            
        buttons = []
        # اضافه شدن دکمه جستجو در بالای لیست
        buttons.append([{"text": "🔍 جستجوی محصول", "callback_data": "search_prod"}])
        
        for cat in categories:
            buttons.append([{"text": f"🏷 {cat}", "callback_data": f"vcat_{cat}"}])
        
        keyboard = {"inline_keyboard": buttons}
        bot.send_message(chat_id, "لطفاً دسته‌بندی را انتخاب کنید یا برای پیدا کردن سریع محصول، روی جستجو بزنید:", keyboard)

def start_search_product(chat_id):
    with Session() as session:
        state = session.query(UserState).filter_by(chat_id=str(chat_id)).first()
        if not state:
            state = UserState(chat_id=str(chat_id))
            session.add(state)
        state.state = 'vendor_search_prod'
        session.commit()
    bot.send_message(chat_id, "🔍 لطفاً **بخشی از نام محصول** مورد نظر خود را ارسال کنید:\n(مثلاً بنویسید: خوشپخت)")

# تابع جدید برای نمایش محصولات یک دسته خاص جهت ویرایش
def list_vendor_products_by_cat(chat_id, category):
    with Session() as session:
        shops = session.query(Shop).filter_by(is_active=True).all()
        shop = None
        for s in shops:
            if convert_to_english_digits(s.owner_chat_id) == str(chat_id):
                shop = s
                break
        if not shop: return
        
        if category == "سایر":
            products = session.query(Product).filter(
                Product.shop_id == shop.id,
                (Product.category == None) | (Product.category == 'None') | (Product.category == 'empty_desc') | (Product.category == 'سایر')
            ).all()
        else:
            products = session.query(Product).filter_by(shop_id=shop.id, category=category).all()

        if not products:
            bot.send_message(chat_id, "محصولی در این دسته یافت نشد.")
            return
            
        buttons = []
        for p in products:
            buttons.append([{"text": f"📦 {p.name} (قیمت: {format_price(p.price)} - موجودی: {p.stock})", "callback_data": f"editvp_{p.id}"}])
        
        # دکمه بازگشت به دسته‌بندی‌ها
        buttons.append([{"text": "🔙 بازگشت به دسته‌بندی‌ها", "callback_data": "manage_cats"}])
        
        keyboard = {"inline_keyboard": buttons}
        bot.send_message(chat_id, "لطفاً محصولی که می‌خواهید ویرایش یا حذف کنید را انتخاب کنید:", keyboard)

def show_edit_product_menu(chat_id, prod_id):
    with Session() as session:
        p = session.query(Product).get(prod_id)
        if not p: return
        keyboard = {
            "inline_keyboard": [
                [{"text": "✏️ ویرایش نام", "callback_data": f"editn_{p.id}"}],
                [{"text": "💵 ویرایش قیمت", "callback_data": f"editp_{p.id}"}],
                [{"text": "📊 ویرایش موجودی", "callback_data": f"edits_{p.id}"}],
                [{"text": "🗑 حذف محصول", "callback_data": f"delvp_{p.id}"}]
            ]
        }
        bot.send_message(chat_id, f"مدیریت محصول:\n📦 {p.name}", keyboard)

def start_edit_name(chat_id, prod_id):
    with Session() as session:
        try:
            state = session.query(UserState).filter_by(chat_id=str(chat_id)).first()
            if not state:
                state = UserState(chat_id=str(chat_id))
                session.add(state)
            state.state = 'vendor_edit_name'
            state.temp_data = str(prod_id)
            session.commit()
            cancel_kb = {"inline_keyboard": [[{"text": "❌ انصراف", "callback_data": "cancel_edit"}]]}
            bot.send_message(chat_id, "لطفاً **نام جدید** محصول را ارسال کنید:", cancel_kb)
        except Exception as e:
            session.rollback()
            print(f"DB Error in start_edit_name: {e}")

def start_edit_price(chat_id, prod_id):
    with Session() as session:
        try:
            state = session.query(UserState).filter_by(chat_id=str(chat_id)).first()
            if not state:
                state = UserState(chat_id=str(chat_id))
                session.add(state)
            state.state = 'vendor_edit_price'
            state.temp_data = str(prod_id)
            session.commit()
        except Exception as e:
            session.rollback()
    bot.send_message(chat_id, "لطفاً **قیمت جدید** را به تومان وارد کنید (فقط عدد):")

def start_edit_stock(chat_id, prod_id):
    with Session() as session:
        state = session.query(UserState).filter_by(chat_id=str(chat_id)).first()
        if not state:
            state = UserState(chat_id=str(chat_id))
            session.add(state)
        state.state = 'vendor_edit_stock'
        state.temp_data = str(prod_id)
        session.commit()
    bot.send_message(chat_id, "لطفاً **موجودی جدید** را وارد کنید (فقط عدد):")

def delete_vendor_product(chat_id, prod_id):
    with Session() as session:
        p = session.query(Product).get(prod_id)
        if p:
            session.delete(p)
            session.commit()
            bot.send_message(chat_id, f"✅ محصول '{p.name}' حذف شد.")

def accept_order(chat_id, order_id):
    with Session() as session:
        order = session.query(Order).get(order_id)
        if not order: return
        if order.status == 'accepted':
            bot.send_message(chat_id, "این سفارش قبلاً تایید شده است.")
            return
        order.status = 'accepted'
        session.commit()
        
        customer_msg = f"✅ سفارش شما با کد {order.id} توسط فروشنده تایید شد و در حال آماده‌سازی است.\n💰 مبلغ قابل پرداخت: {format_price(order.total_price)} تومان\n\nلطفاً روش پرداخت خود را انتخاب کنید:"
        pay_keyboard = {
            "inline_keyboard": [
                [{"text": "💳 پرداخت آنلاین (کارت به کارت)", "callback_data": f"payonline_{order.id}"}],
                [{"text": "🚪 پرداخت درب منزل (کارتی/نقدی)", "callback_data": f"paycod_{order.id}"}]
            ]
        }
        try: bot.send_message(order.customer_id, customer_msg, pay_keyboard)
        except: pass
        bot.send_message(chat_id, "شما این سفارش را تایید کردید. در انتظار انتخاب روش پرداخت توسط مشتری...")

def handle_payment_online(chat_id, order_id):
    with Session() as session:
        order = session.query(Order).get(order_id)
        if not order: return
        
        customer_msg = "شما گزینه پرداخت آنلاین را انتخاب کردید.\n\nلطفاً مبلغ سفارش را به کارت زیر واریز کنید:\n💳 ۶۱۰۴-۳۳۷۵-xxxx-xxxx\nبه نام: فروشنده تست\n\nپس از واریز، عکس رسید را به همین چت ارسال کنید تا سفارش شما نهایی شود."
        bot.send_message(chat_id, customer_msg)
        
        shop = session.query(Shop).get(order.shop_id) if order.shop_id else None
        if shop:
            vendor_msg = f"🔔 مشتری (کد سفارش {order.id}) گزینه 'پرداخت آنلاین' را انتخاب کرد.\nلطفاً منتظر ارسال عکس رسید کارت به کارت توسط مشتری باشید."
            try: bot.send_message(shop.owner_chat_id, vendor_msg)
            except: pass

def handle_payment_cod(chat_id, order_id):
    with Session() as session:
        order = session.query(Order).get(order_id)
        if not order: return
        
        customer_msg = "شما گزینه پرداخت درب منزل را انتخاب کردید.\n\nℹ️ لطفاً مبلغ سفارش را آماده کنید. پیک موتوری به همراه خود کارت‌خوان سیار (پوز) خواهد داشت."
        bot.send_message(chat_id, customer_msg)
        
        shop = session.query(Shop).get(order.shop_id) if order.shop_id else None
        if shop:
            vendor_msg = f"🔔 مشتری (کد سفارش {order.id}) گزینه 'پرداخت درب منزل' را انتخاب کرد.\nلطفاً به پیک خود اطلاع دهید که کارت‌خوان سیار (پوز) همراه خود ببرد."
            try: bot.send_message(shop.owner_chat_id, vendor_msg)
            except: pass

def handle_customer_photo(chat_id, user_id, photo):
    print(f"DEBUG: Received photo from customer {user_id}")
    with Session() as session:
        # پیدا کردن آخرین سفارش این مشتری
        order = session.query(Order).filter_by(customer_id=str(user_id)).order_by(Order.id.desc()).first()
        if not order:
            bot.send_message(chat_id, "شما سفارش فعالی ندارید. لطفاً ابتدا خرید خود را نهایی کنید.")
            return

        shop = session.query(Shop).get(order.shop_id)
        if not shop:
            bot.send_message(chat_id, "فروشگاه مربوط به سفارش شما یافت نشد.")
            return

        file_id = photo[-1]['file_id'] if isinstance(photo, list) else photo['file_id']
        caption = f"📸 رسید پرداخت جدید\n\nکد سفارش: {order.id}\n📞 شماره مشتری: {order.phone}\n💰 مبلغ: {format_price(order.total_price)} تومان\n\nلطفاً صحت واریز را بررسی کرده و در صورت تایید، سفارش را ارسال نمایید."

        try:
            # فوروارد عکس برای مغازه‌دار
            bot.send_photo(shop.owner_chat_id, file_id, caption)
            # پیام تایید به مشتری
            bot.send_message(chat_id, "✅ رسید شما دریافت شد و برای فروشنده ارسال گردید.\nپس از تایید واریز وجه توسط فروشنده، سفارش شما ارسال خواهد شد. سپاس از صبوری شما!")
        except Exception as e:
            print(f"Error forwarding photo to vendor: {e}")
            bot.send_message(chat_id, "⚠️ خطا در ارسال رسید به فروشنده. لطفاً کمی بعد دوباره تلاش کنید یا با پشتیبانی تماس بگیرید.")

