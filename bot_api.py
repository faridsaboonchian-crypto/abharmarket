# bot_api.py
import requests
import json

session = requests.Session()
session.trust_env = False

class BotAPI:
    def __init__(self, token):
        self.token = token
        self.base_url = f"https://tapi.bale.ai/bot{token}/"

    def send_message(self, chat_id, text, keyboard=None):
        payload = {'chat_id': chat_id, 'text': text}
        if keyboard:
            payload['reply_markup'] = json.dumps(keyboard)
        try:
            session.post(self.base_url + "sendMessage", data=payload, timeout=10)
        except Exception as e:
            print(f"API Error: {e}")

    # متد جدید برای ارسال عکس با کپشن
    def send_photo(self, chat_id, photo_file_id, caption, keyboard=None):
        payload = {'chat_id': chat_id, 'photo': photo_file_id, 'caption': caption}
        if keyboard:
            payload['reply_markup'] = json.dumps(keyboard)
        try:
            session.post(self.base_url + "sendPhoto", data=payload, timeout=10)
        except Exception as e:
            print(f"API Photo Error: {e}")