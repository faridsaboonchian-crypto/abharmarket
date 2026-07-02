# main.py
import requests
import time
import os
from database import Session, UserState
from handlers import (start_bot, show_shops_menu, show_shop_products, show_category_products, 
                      show_cart, add_to_cart, start_checkout, process_checkout_step, 
                      start_vendor_panel, process_vendor_step, list_vendor_products, 
                      delete_vendor_product, show_edit_product_menu, start_edit_price, 
                      start_edit_stock, start_edit_name, accept_order,
                      show_admin_panel, list_shops, list_shops_for_delete, delete_shop, 
                      process_admin_step, reset_state_to_main, bot)
from config import BOT_TOKEN

session = requests.Session()
session.trust_env = False

API_URL = f"https://tapi.bale.ai/bot{BOT_TOKEN}/"
UPDATE_FILE = "last_update_id.txt"

def load_last_update_id():
    if os.path.exists(UPDATE_FILE):
        with open(UPDATE_FILE, "r") as f:
            try: return int(f.read().strip())
            except: return 0
    return 0

def save_last_update_id(uid):
    with open(UPDATE_FILE, "w") as f:
        f.write(str(uid))

def get_updates(offset):
    try:
        url = f"{API_URL}getUpdates?offset={offset}&timeout=10"
        res = session.get(url, timeout=15)
        if res.status_code == 200:
            data = res.json()
            if data.get('ok'): return data.get('result', [])
    except:
        pass
    return []

def main():
    last_update_id = load_last_update_id()
    print(f"🚀 ربات AbharMarket روشن شد. (آخرین آپدیت: {last_update_id})")
    
    while True:
        updates = get_updates(last_update_id + 1)
        
        for update in updates:
            current_update_id = update.get('update_id')
            save_last_update_id(current_update_id)
            last_update_id = current_update_id
            
            message = update.get('message')
            callback = update.get('callback_query')
            
            chat_id = None
            text = ""
            user_id = None
            photo = None
            
            if message:
                chat_id = message['chat']['id']
                text = message.get('text', '')
                user_id = message['from']['id']
                photo = message.get('photo')
            elif callback:
                chat_id = callback['message']['chat']['id']
                text = callback.get('data', '')
                user_id = callback['from']['id']
            else:
                continue
                
            print(f"📩 پیام از {chat_id}: {'عکس' if photo else text}")

            try:
                with Session() as s:
                    state_obj = s.query(UserState).filter_by(chat_id=str(chat_id)).first()
                    current_state = state_obj.state if state_obj else 'main'

                # ۱. دستورات سراسری
                if text.startswith('/start'):
                    parts = text.split()
                    deep_link = parts[1] if len(parts) > 1 else None
                    start_bot(chat_id, deep_link)
                elif text == '🔙 بازگشت' or text == '🔙 بازگشت به منوی مشتری':
                    reset_state_to_main(chat_id)
                    
                # ۲. دکمه‌های منوی اصلی مشتری (این بخش بالاتر آمد تا گیر نکنند)
                elif text == "🛒 مشاهده محصولات":
                    show_shops_menu(chat_id)
                elif text == "🛍 سبد خرید":
                    show_cart(chat_id, user_id)
                elif text == "👤 پشتیبانی":
                    bot.send_message(chat_id, "برای پشتیبانی با شماره 0912... تماس بگیرید.")
                    
                # ۳. دکمه‌های شیشه‌ای (Callback ها)
                elif text.startswith('add_'):
                    prod_id = int(text.replace('add_', ''))
                    add_to_cart(chat_id, user_id, prod_id)
                elif text.startswith('shop_'):
                    shop_id = int(text.replace('shop_', ''))
                    show_shop_products(chat_id, shop_id)
                elif text.startswith('catshop_'):
                    parts = text.split('_', 2)
                    shop_id = int(parts[1])
                    category = parts[2]
                    show_category_products(chat_id, shop_id, category)
                elif text.startswith('dels_'):
                    shop_id = int(text.replace('dels_', ''))
                    delete_shop(chat_id, shop_id)
                elif text.startswith('delvp_'):
                    prod_id = int(text.replace('delvp_', ''))
                    delete_vendor_product(chat_id, prod_id)
                elif text.startswith('editvp_'):
                    prod_id = int(text.replace('editvp_', ''))
                    show_edit_product_menu(chat_id, prod_id)
                elif text.startswith('editp_'):
                    prod_id = int(text.replace('editp_', ''))
                    start_edit_price(chat_id, prod_id)
                elif text.startswith('edits_'):
                    prod_id = int(text.replace('edits_', ''))
                    start_edit_stock(chat_id, prod_id)
                elif text.startswith('editn_'):
                    prod_id = int(text.replace('editn_', ''))
                    start_edit_name(chat_id, prod_id)
                elif text.startswith('accept_'):
                    order_id = int(text.replace('accept_', ''))
                    accept_order(chat_id, order_id)
                elif text == 'checkout':
                    start_checkout(chat_id, user_id)
                    
                # ۴. مدیریت پنل‌ها
                elif current_state.startswith('admin') or (current_state == 'main' and text in ['➕ ثبت فروشگاه جدید', '📊 آمار سیستم', '🏪 لیست فروشگاه‌ها', '🗑 حذف فروشگاه', '/admin']):
                    process_admin_step(chat_id, text)
                elif current_state.startswith('vendor'):
                    process_vendor_step(chat_id, text, photo)
                elif current_state.startswith('waiting'):
                    process_checkout_step(chat_id, user_id, text)
                    
            except Exception as e:
                print(f"⚠️ خطا در پردازش: {e}")
                
        time.sleep(0.5)

if __name__ == '__main__':
    main()