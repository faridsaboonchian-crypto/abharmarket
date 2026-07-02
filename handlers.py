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
    buttons = ['➕ ثبت فروشگاه جدید', '📊 آمار سیستم', '🏪 لیست فروشگاه‌ها', '🗑 حذف فروشگاه', '🔙 بازگشت', '➕ افزودن محصول جدید', '📦 مدیریت محصولات', '🔙 بازگشت به منوی مشتری', '🛒 مشاهده محصولات', '🛍 سبد خرید', '👤 پشتیبانی']
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

# ---------------- پنل مدیریت شما ----------------
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

# ---------------- بخش مشتری ----------------
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
        for cat in categories:
            buttons.append([{"text": f"🏷 {cat}", "callback_data": f"catshop_{shop_id}_{cat}"}])
        keyboard = {"inline_keyboard": buttons}
        bot.send_message(chat_id, f"🏦 فروشگاه '{shop.name}'\nلطفاً دسته‌بندی مورد نظر خود را انتخاب کنید:", keyboard)

def show_category_products(chat_id, shop_id, category):
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
            
        bot.send_message(chat_id, f"🛍️ دسته‌بندی: {category}")
        
        for p in products:
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

def add_to_cart(chat_id, user_id, product_id):
    with Session() as session:
        state = session.query(UserState).filter_by(chat_id=str(chat_id)).first()
        if not state:
            state = UserState(chat_id=str(chat_id))
            session.add(state)
        # تنظیم وضعیت برای پرسیدن تعداد
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
        
        prod_id = int(state.temp_data)
        product = session.query(Product).get(prod_id)
        if not product:
            bot.send_message(chat_id, "⚠️ محصول یافت نشد.")
            state.state = 'main'
            session.commit()
            return
            
        if product.stock < quantity:
            bot.send_message(chat_id, f"⚠️ موجودی کافی نیست. حداکثر {product.stock} عدد موجود است.")
            state.state = 'main'
            session.commit()
            return
            
        cart_item = session.query(Cart).filter_by(customer_eitaa_id=str(user_id), product_id=prod_id).first()
        if cart_item:
            cart_item.quantity += quantity
        else:
            cart_item = Cart(customer_eitaa_id=str(user_id), product_id=prod_id, quantity=quantity)
            session.add(cart_item)
            
        # ریست کردن State به منوی اصلی
        state.state = 'main'
        state.temp_data = None
        session.commit()
        
    bot.send_message(chat_id, f"✅ {quantity} عدد از '{product.name}' به سبد شما اضافه شد.")

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
            state.temp_data = f"phone|||{text}"
            state.state = 'waiting_address'
            session.commit()
            bot.send_message(chat_id, "✅ شماره ثبت شد.\n📍 حالا **آدرس کامل** را وارد کنید:")
            return

        elif state.state == 'waiting_address':
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
                state.state = 'main'
                session.commit()
                return

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
                    shop_orders[p.shop_id] = {
                        "items_text": "",
                        "total": 0,
                        "owner_id": shop.owner_chat_id,
                        "shop_name": shop.name
                    }
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

            customer_msg = f"🎉 سفارش شما با کد {new_order.id} ثبت شد!\n\n"
            customer_msg += f"📦 **اقلام سفارش:**\n{items_text_customer}\n"
            customer_msg += f"💰 **مبلغ کل: {format_price(total_price)} تومان**\n\n"
            customer_msg += f"📍 آدرس: {new_order.address}\n📞 تلفن: {new_order.phone}\n\nسفارش شما در انتظار تایید فروشنده است."
            bot.send_message(chat_id, customer_msg, main_keyboard())

            for shop_id, data in shop_orders.items():
                vendor_msg = f"🔔 سفارش جدید برای فروشگاه شما ({data['shop_name']})!\n\n"
                vendor_msg += f"کد سفارش: {new_order.id}\n📞 شماره مشتری: {new_order.phone}\n📍 آدرس: {new_order.address}\n\n"
                vendor_msg += f"📦 **اقلام این فروشگاه:**\n{data['items_text']}\n"
                vendor_msg += f"💰 مبلغ قابل دریافت شما: {format_price(data['total'])} تومان"
                
                accept_keyboard = {"inline_keyboard": [[{"text": "✅ تایید سفارش و ارسال", "callback_data": f"accept_{new_order.id}"}]]}
                try:
                    bot.send_message(str(data['owner_id']), vendor_msg, accept_keyboard)
                except Exception as e:
                    print(f"⚠️ خطا در ارسال به مغازه‌دار: {e}")

            admin_msg = f"🔔 سفارش جدید در سیستم!\n\nکد: {new_order.id}\n📞 شماره: {new_order.phone}\n📍 آدرس: {new_order.address}\n\n📦 **کل اقلام:**\n{items_text_customer}\n💰 مبلغ کل: {format_price(total_price)} تومان"
            try:
                bot.send_message(ADMIN_ID, admin_msg)
            except: pass
            return

# ---------------- بخش پنل مغازه‌دار ----------------
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
            
        buttons = []
        for p in products:
            buttons.append([{"text": f"📦 {p.name} (قیمت: {format_price(p.price)} - موجودی: {p.stock})", "callback_data": f"editvp_{p.id}"}])
        
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
        customer_msg = f"✅ سفارش شما با کد {order.id} توسط فروشنده تایید شد و در حال آماده‌سازی است.\nبه زودی کالا برای شما ارسال خواهد شد."
        try: bot.send_message(order.customer_id, customer_msg)
        except: pass
        bot.send_message(chat_id, "شما این سفارش را تایید کردید. مشتری مطلع شد.")

def process_vendor_step(chat_id, text, photo=None):
    text = convert_to_english_digits(text)
    with Session() as session:
        state = session.query(UserState).filter_by(chat_id=str(chat_id)).first()
        if not state: return

        if text == '➕ افزودن محصول جدید' and state.state == 'vendor_menu':
            state.state = 'vendor_name'
            session.commit()
            bot.send_message(chat_id, "۱. **نام محصول** را وارد کنید:")
            return

        if text == '📦 مدیریت محصولات' and state.state == 'vendor_menu':
            list_vendor_products(chat_id)
            return

        if state.state == 'vendor_edit_name':
            if is_button(text) or not text or len(text) < 2:
                bot.send_message(chat_id, "⚠️ لطفاً یک نام معتبر (حداقل ۲ حرف) تایپ کنید:")
                return
            try: prod_id = int(state.temp_data)
            except (ValueError, TypeError):
                bot.send_message(chat_id, "⚠️ خطا در شناسایی محصول.", vendor_keyboard())
                state.state = 'vendor_menu'; state.temp_data = None; session.commit(); return

            p = session.query(Product).get(prod_id)
            if p:
                p.name = text
                session.commit()
                bot.send_message(chat_id, "✅ نام محصول با موفقیت بروزرسانی شد.", vendor_keyboard())
            else: bot.send_message(chat_id, "⚠️ محصول یافت نشد.")
            state.state = 'vendor_menu'; state.temp_data = None; session.commit()
            return

        if state.state == 'vendor_edit_price':
            if not text.isdigit():
                bot.send_message(chat_id, "⚠️ قیمت باید فقط عدد باشد. دوباره وارد کنید:")
                return
            try: prod_id = int(state.temp_data)
            except (ValueError, TypeError):
                bot.send_message(chat_id, "⚠️ خطا در شناسایی محصول.", vendor_keyboard())
                state.state = 'vendor_menu'; state.temp_data = None; session.commit(); return

            p = session.query(Product).get(prod_id)
            if p:
                p.price = float(text)
                session.commit()
                bot.send_message(chat_id, "✅ قیمت با موفقیت بروزرسانی شد.", vendor_keyboard())
            else: bot.send_message(chat_id, "⚠️ محصول یافت نشد.")
            state.state = 'vendor_menu'; state.temp_data = None; session.commit()
            return

        elif state.state == 'vendor_edit_stock':
            if not text.isdigit():
                bot.send_message(chat_id, "⚠️ موجودی باید فقط عدد باشد. دوباره وارد کنید:")
                return
            try: prod_id = int(state.temp_data)
            except (ValueError, TypeError):
                bot.send_message(chat_id, "⚠️ خطا در شناسایی محصول.", vendor_keyboard())
                state.state = 'vendor_menu'; state.temp_data = None; session.commit(); return

            p = session.query(Product).get(prod_id)
            if p:
                p.stock = int(text)
                session.commit()
                bot.send_message(chat_id, "✅ موجودی با موفقیت بروزرسانی شد.", vendor_keyboard())
            else: bot.send_message(chat_id, "⚠️ محصول یافت نشد.")
            state.state = 'vendor_menu'; state.temp_data = None; session.commit()
            return

        if state.state == 'vendor_name':
            if is_button(text):
                bot.send_message(chat_id, "⚠️ لطفاً یک نام معتبر تایپ کنید:")
                return
            state.temp_data = f"name:{text}"
            state.state = 'vendor_price'
            session.commit()
            bot.send_message(chat_id, "۲. **قیمت** را به تومان وارد کنید (فقط عدد):")
            return

        elif state.state == 'vendor_price':
            if not text.isdigit():
                bot.send_message(chat_id, "⚠️ قیمت باید عدد باشد:")
                return
            state.temp_data += f"|price:{text}"
            state.state = 'vendor_stock'
            session.commit()
            bot.send_message(chat_id, "۳. **موجودی** را وارد کنید (فقط عدد):")
            return

        elif state.state == 'vendor_stock':
            if not text.isdigit():
                bot.send_message(chat_id, "⚠️ موجودی باید عدد باشد:")
                return
            state.temp_data += f"|stock:{text}"
            state.state = 'vendor_cat'
            session.commit()
            bot.send_message(chat_id, "۴. **دسته‌بندی محصول** را وارد کنید (مثلاً: روغن، برنج، شوینده):")
            return

        elif state.state == 'vendor_cat':
            if is_button(text) or text == 'ندارد':
                bot.send_message(chat_id, "⚠️ لطفاً دسته‌بندی معتبر وارد کنید (مثلاً روغن):")
                return
            state.temp_data += f"|cat:{text}"
            state.state = 'vendor_desc'
            session.commit()
            bot.send_message(chat_id, "۵. **توضیحات** را وارد کنید (اگر ندارد بنویسید 'ندارد'):")
            return

        elif state.state == 'vendor_desc':
            desc_text = text if text != 'ندارد' else 'empty_desc'
            state.temp_data += f"|desc:{desc_text}"
            state.state = 'vendor_photo'
            session.commit()
            bot.send_message(chat_id, "۶. عکس محصول را ارسال کنید.")
            return

        elif state.state == 'vendor_photo':
            if not photo:
                bot.send_message(chat_id, "⚠️ لطفاً یک عکس ارسال کنید.")
                return
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
            state.state = 'vendor_menu'
            state.temp_data = None
            session.commit()
            bot.send_message(chat_id, f"✅ محصول '{new_product.name}' ثبت شد!", vendor_keyboard())
            return