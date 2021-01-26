import os
import sys
import time

import requests
import telegram

from dotenv import load_dotenv
from requests.exceptions import ConnectionError, ReadTimeout, HTTPError
from textwrap import dedent
from urllib.parse import urljoin


DVMN_URL = 'https://dvmn.org/'
DVMN_LONG_POLLING_URL = 'https://dvmn.org/api/long_polling/'

RESULT_TEXTS = {
    'negative': 'К сожалению, в работе нашлись ошибки.',
    'positive': 'Работа принята. Можно приступать к следующему уроку.'
}


def send_message(bot, attempt, chat_id):
    lesson_title = attempt['lesson_title']
    lesson_url = urljoin(DVMN_URL, attempt['lesson_url'])
    if attempt['is_negative']:
        current_result_text = RESULT_TEXTS['negative']
    else:
        current_result_text = RESULT_TEXTS['positive']
    message = dedent(f'''\
        У вас проверили урок "{lesson_title}".
        
        {current_result_text}
        
        {lesson_url}
    ''')

    bot.send_message(chat_id=chat_id, text=message)


def main():
    load_dotenv()
    chat_id = os.getenv('TG_CHAT_ID')
    bot = telegram.Bot(token=os.getenv('TG_BOT_TOKEN'))
    params = {}
    headers = {"Authorization": os.getenv('DVMN_API_TOKEN')}
    while True:
        try:
            response = requests.get(
                DVMN_LONG_POLLING_URL, headers=headers,
                params=params, timeout=91
            )
            response.raise_for_status()
            decoded_response = response.json()
            if 'error' in decoded_response:
                raise HTTPError(decoded_response['error'])
            if decoded_response['status'] == 'timeout':
                params['timestamp'] = decoded_response['timestamp_to_request']
            elif decoded_response['status'] == 'found':
                attempt = decoded_response['new_attempts'][0]
                send_message(bot, attempt, chat_id)
                params['timestamp'] = decoded_response['last_attempt_timestamp']
        except ConnectionError as conn_err:
            print(conn_err, file=sys.stderr)
            time.sleep(3)
        except ReadTimeout:
            continue


if __name__ == "__main__":
    main()
