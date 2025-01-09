#!/usr/bin/env python3
import argparse
from io import BufferedReader
from os.path import expanduser
from typing import Dict, Optional

import ftputil
import requests
from ftputil.file import FTPFile

global debug
debug: bool


def telegram_bot_sendphoto(photo: FTPFile | BufferedReader, chat_id: str, disable_notification: bool = True, message_thread_id: Optional[str] = None) -> Dict:
    # curl -F photo=@"./image.jpg" https://api.telegram.org/bot$token/sendPhoto?chat_id=$chat_id

    home = expanduser("~")
    with open(f"{home}/Documents/erinner_bot/TOKEN", 'r') as f:
        bot_token = f.read()
    if not bot_token:
        raise RuntimeError("No bot token found")

    files = {'photo': photo}
    data = {
        'chat_id': chat_id,
        'disable_notification': disable_notification,
    }
    if message_thread_id is not None:
        data['message_thread_id'] = message_thread_id

    url = f"https://api.telegram.org/bot{bot_token}/sendPhoto"
    response = requests.post(url, files=files, data=data)
    if debug:
        print(type(response), response)
    response_json: Dict = response.json()
    return response_json


def read_string_from_file(file_path: str) -> Optional[str]:
    try:
        with open(file_path, 'r') as f:
            return f.read()
    except FileNotFoundError:
        return None


def check_if_latest_file_is_already_sent(latest_filename: str) -> bool:
    last_filename = read_string_from_file("latest_filename")

    if latest_filename == last_filename:
        return True
    else:
        with open("latest_filename", 'w') as f:
            f.write(latest_filename)
    return False


def argparse_do() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="send photo of snow")
    parser.add_argument("-d", help="enable debug mode", default=False, action="store_true",)

    return parser.parse_args()


def main() -> None:
    args = argparse_do()
    global debug
    debug = args.d

    home = expanduser("~")
    with open(f"{home}/Documents/erinner_bot/server-mail.id", 'r') as f:
        chat_id = f.read()

    message_thread_id = "4738"
    user = read_string_from_file("user")
    passwd = read_string_from_file("passwd")
    with ftputil.FTPHost('pt-frohnau.local', user, passwd) as ftp:  # connect to host, default port
        ftp.chdir('kamera')               # change into "debian" directory

        files_list = ftp.listdir(".")
        files_list = [elem for elem in files_list if elem.endswith(".jpg")]  # remove non *.jpg files
        files_list = sorted(files_list)  # sort files by filename (by time taken)

        if check_if_latest_file_is_already_sent(files_list[-1]):
            return

        with ftp.open(files_list[-1], 'rb') as photo:
            response = telegram_bot_sendphoto(photo, chat_id, message_thread_id=message_thread_id)
            if debug:
                print(response)


if __name__ == "__main__":
    main()
