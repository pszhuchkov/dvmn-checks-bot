import os
import sys
import time

import requests
import telegram

from dotenv import load_dotenv
from pprint import pprint
from requests.exceptions import ConnectionError, ReadTimeout
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
    message = f'У вас проверили урок "{lesson_title}".\n\n' \
              f'{current_result_text}\n\n' \
              f'{lesson_url}'
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
                params=params, timeout=95
            )
            if response.json()['status'] == 'timeout':
                params['timestamp'] = response.json()['timestamp_to_request']
            elif response.json()['status'] == 'found':
                attempt = response.json()['new_attempts'][0]
                send_message(bot, attempt)
                params['timestamp'] = response.json()['last_attempt_timestamp']
                pprint(response.json())
        except ConnectionError as conn_err:
            print(conn_err, file=sys.stderr)
            time.sleep(5)
        except ReadTimeout as timeout_err:
            print(timeout_err, file=sys.stderr)
            time.sleep(5)


if __name__ == "__main__":
    main()
