#!/usr/bin/env python3
import argparse
import asyncio
import datetime
import os
import statistics
from io import BufferedReader
from os.path import expanduser
from typing import Dict, Optional, Tuple

import ftputil
import holidays
import python_weather
import requests
from ftputil.file import FTPFile
from python_weather.forecast import Forecast

global debug
debug: bool


def telegram_bot_sendphoto(photo: FTPFile | BufferedReader, chat_id: str, caption: Optional[str] = None, disable_notification: bool = True, message_thread_id: Optional[str] = None) -> Dict:
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
        "parse_mode": "MarkdownV2",
    }
    if caption is not None:
        escape_chars = ['_', '*', '[', ']', '(', ')', '~', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']  # not including "`", which I use to format as code
        for char in escape_chars:
            caption = caption.replace(char, f"\\{char}")
        data['caption'] = caption
    if message_thread_id is not None:
        data['message_thread_id'] = message_thread_id

    url = f"https://api.telegram.org/bot{bot_token}/sendPhoto"
    response = requests.post(url, files=files, data=data)
    if debug:
        print(type(response), response)
    response_json: Dict = response.json()
    return response_json


def replace_minus_sign(text: str) -> str:
    """Replace ASCII dash with Unicode minus sign for negative numbers."""
    return text.replace('-', '−')


def read_string_from_file(file_path: str) -> Optional[str]:
    try:
        with open(file_path, 'r') as f:
            return f.read().strip()
    except FileNotFoundError:
        return None


def check_if_latest_file_is_already_sent(latest_filename: str) -> bool:
    last_filename = read_string_from_file("latest_filename")

    if latest_filename == last_filename:
        return True
    return False


def set_filename_sent(latest_filename: str) -> None:
    with open("latest_filename", 'w') as f:
        f.write(latest_filename)


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="send photo of snow")
    parser.add_argument("-d", help="enable debug mode", default=False, action="store_true",)

    args = parser.parse_args()

    global debug
    debug = args.d

    return args


def get_forecasts() -> Dict:
    return_value = asyncio.run(getweather(str(read_string_from_file("location"))))
    if return_value is None:
        raise RuntimeError("Could not get weather")

    weather_metric, weather_metric_converted = return_value

    # get the weather forecast for a few days
    forecasts: Dict[datetime.datetime, Dict[str, str | float]] = {}
    for weather in [weather_metric, weather_metric_converted]:
        for daily in weather:
            day_date: datetime.date = daily.date
            for hourly in daily:
                forecast_datetime = datetime.datetime(day_date.year, day_date.month, day_date.day, hourly.time.hour, hourly.time.minute)
                forecast_new: Dict[str, str | float] = {"temperature": float(hourly.temperature), "description": str(hourly.description), "kind": str(hourly.kind)}
                for key, value in forecast_new.items():
                    forecasts.setdefault(forecast_datetime, {})
                    old_value = forecasts.get(forecast_datetime, {}).get(key)
                    if old_value is None or old_value == value:
                        forecasts[forecast_datetime][key] = forecasts[forecast_datetime].get(key, value)
                    else:
                        if type(old_value) is float and type(value) is float:
                            # average new value with old value
                            forecasts[forecast_datetime][key] = old_value * 0.28 + value * 0.72  # 0.28 is experimentally confirmed by spreadsheet converting rounded c and f back to c and minimizing median and average error
                        else:
                            forecasts[forecast_datetime][key] = f"{old_value}, {value}"
    return forecasts


def convert_f_to_c(temp_in_fahrenheit: int | float) -> float:
    return (float(temp_in_fahrenheit) - 32) * 5 / 9


async def getweather(city_name: str) -> Tuple[Forecast, Forecast]:
    client: python_weather.Client
    async with python_weather.Client(unit=python_weather.IMPERIAL) as client:
        # fetch a weather forecast from a city
        weather_imperial = await client.get(city_name)

    async with python_weather.Client(unit=python_weather.METRIC) as client:
        # fetch a weather forecast from a city
        weather_metric = await client.get(city_name)

    for daily in weather_imperial:
        for hourly in daily:
            hourly.temperature = convert_f_to_c(hourly.temperature)

    return weather_metric, weather_imperial


def skip_image_sending(now: datetime.datetime, is_holiday: bool, last_modified_delta: datetime.timedelta) -> bool:
    now_hour_float = now.hour + now.minute / 60
    if now_hour_float <= 6.2 and not is_holiday or now_hour_float <= 7.2 and is_holiday:
        # print("don't send images during the night/morning")
        return True

    if now_hour_float >= 7.5 and not is_holiday or now_hour_float >= 9.5 and is_holiday:
        if last_modified_delta < datetime.timedelta(hours=3):
            # print("don't send frequent images during the day")
            return True

    if now_hour_float >= 19.4:
        # print("don't send images during the night")
        return True

    return False


def main() -> None:
    parse_arguments()
    global debug

    forecasts = get_forecasts()

    now = datetime.datetime.now()

    temps = []
    description_and_kind = []
    dt: datetime.datetime
    for dt, value_dict in forecasts.items():
        delta_hours = (dt - now).total_seconds() / 60 / 60
        if -7.5 <= delta_hours <= 7.5:  # not too old, not too far in the future
            temps.append(value_dict["temperature"])

            desc = value_dict["description"]
            kind = value_dict["kind"]
            if kind.lower() != desc.lower():
                desc += f" ({kind})"

            formatted_line = f"{dt.time().hour:02}:{dt.time().minute:02}{value_dict['temperature']: >-6.2f} °C  {desc}"
            description_and_kind.append(replace_minus_sign(formatted_line))

    temp_median = statistics.median(temps)
    temp_mean = statistics.mean(temps)
    temp_min = min(temps)
    temp_max = max(temps)
    temp_range = temp_max - temp_min
    temp_deviation = statistics.stdev(temps)
    list_of_temps = '\n'.join(description_and_kind)
    caption_line = f"min={temp_min:.2f} med={temp_median:.2f} avg={temp_mean:.2f} max={temp_max:.2f} rge={temp_range:.2f} dev={temp_deviation:.2f}\n⁰C={temps}\n`{list_of_temps}`"
    caption = replace_minus_sign(caption_line)
    print(caption)

    # get time last modified of file "latest_filename"
    try:
        last_modified = datetime.datetime.fromtimestamp(os.path.getmtime("latest_filename"))
    except FileNotFoundError:
        last_modified = datetime.datetime.fromtimestamp(0)
    last_modified_delta = now - last_modified
    if last_modified_delta.total_seconds() < 60 * 30:
        print("last sent was modified less than n minutes ago")
        return

    weekday = now.weekday()  # Monday == 0 ... Sunday == 6
    holidays_de_be = holidays.country_holidays("DE", subdiv="BE")
    is_holiday = weekday == 6 or now.date() in holidays_de_be

    if skip_image_sending(now, is_holiday, last_modified_delta):
        return

    if temp_min > 3:
        print("probably no snow if temperature is entirely above n °C")
        return

    home = expanduser("~")
    with open(f"{home}/Documents/erinner_bot/server-mail.id", 'r') as f:
        chat_id = f.read()

    user = read_string_from_file("user")
    passwd = read_string_from_file("passwd")
    with ftputil.FTPHost('pt-frohnau.local', user, passwd) as ftp:
        ftp.chdir('kamera')

        files_list = ftp.listdir(".")
        files_list = [elem for elem in files_list if elem.endswith(".jpg")]  # remove non *.jpg files
        files_list = sorted(files_list)  # sort files by filename (by time taken)

        if check_if_latest_file_is_already_sent(files_list[-1]):
            print("latest file already sent")
            return

        caption += "\n" + files_list[-1]
        with ftp.open(files_list[-1], 'rb') as photo:
            response = telegram_bot_sendphoto(photo=photo, chat_id=chat_id, message_thread_id="4738", caption=caption)
            if response["ok"]:
                set_filename_sent(files_list[-1])
            if debug:
                print(response)


if __name__ == "__main__":
    main()
