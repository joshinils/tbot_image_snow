#!/usr/bin/env python3
from os.path import expanduser
from typing import Dict, Optional

import requests


def telegram_bot_sendphoto(photo_path: str, chat_id: str, disable_notification: bool = True, message_thread_id: Optional[str] = None) -> Dict:
    # curl -F photo=@"./image.jpg" https://api.telegram.org/bot$token/sendPhoto?chat_id=$chat_id

    home = expanduser("~")
    with open(f"{home}/Documents/erinner_bot/TOKEN", 'r') as f:
        bot_token = f.read()
    if not bot_token:
        raise RuntimeError("No bot token found")

    url = f"https://api.telegram.org/bot{bot_token}/sendPhoto"
    with open(photo_path, 'rb') as photo:
        files = {'photo': photo}
        data = {
            'chat_id': chat_id,
            'disable_notification': disable_notification,
        }
        if message_thread_id is not None:
            data['message_thread_id'] = message_thread_id

        response = requests.post(url, files=files, data=data)
    print(type(response), response)
    response_json: Dict = response.json()
    return response_json


home = expanduser("~")
with open(f"{home}/Documents/erinner_bot/server-mail.id", 'r') as f:
    server_mail_id = f.read()

thread_id_cam_snow = "4738"

photo_path = "/home/jola/Downloads/test.png"
response = telegram_bot_sendphoto(photo_path, server_mail_id, message_thread_id=thread_id_cam_snow)
print(response)

