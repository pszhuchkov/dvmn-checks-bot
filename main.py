import os
import sys
import time

import requests
import telegram

from dotenv import load_dotenv
from requests.exceptions import ConnectionError, ReadTimeout
from textwrap import dedent
from urllib.parse import urljoin


DVMN_URL = 'https://dvmn.org/'
DVMN_LONG_POLLING_URL = 'https://dvmn.org/api/long_polling/'

RESULT_TEXTS = {
    'negative': 'К сожалению, в работе нашлись ошибки.',
    'positive': 'Работа принята. Можно приступать к следующему уроку.'
}


def send_message(bot, attempt):
    lesson_title = attempt['lesson_title']
    lesson_url = urljoin(DVMN_URL, attempt['lesson_url'])
    if attempt['is_negative']:
        current_result_text = RESULT_TEXTS['negative']
    else:
        current_result_text = RESULT_TEXTS['positive']
    message = dedent(f'''\
        У вас проверили урок "{lesson_title}".
        
        {current_result_text}.
        
        {lesson_url}
    ''')

    bot.send_message(chat_id=os.getenv('TG_CHAT_ID'), text=message)


def main():
    load_dotenv()
    bot = telegram.Bot(token=os.getenv('TG_BOT_TOKEN'))
    params = {}
    headers = {"Authorization": os.getenv('DVMN_API_TOKEN')}
    while True:
        try:
            response = requests.get(
                DVMN_LONG_POLLING_URL, headers=headers,
                params=params, timeout=91
            )
            if response.json()['status'] == 'timeout':
                params['timestamp'] = response.json()['timestamp_to_request']
            elif response.json()['status'] == 'found':
                attempt = response.json()['new_attempts'][0]
                send_message(bot, attempt)
                params['timestamp'] = response.json()['last_attempt_timestamp']
        except ConnectionError as conn_err:
            print(conn_err, file=sys.stderr)
            time.sleep(3)
        except ReadTimeout:
            time.sleep(0.001)


if __name__ == "__main__":
    main()
