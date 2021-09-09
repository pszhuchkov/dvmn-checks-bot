import logging
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

logger = logging.getLogger('Logger')


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


class TelegramLogsHandler(logging.Handler):

    def __init__(self, bot, chat_id):
        super().__init__()
        self.bot = bot
        self.chat_id = chat_id

    def emit(self, record):
        log_entry = self.format(record)
        self.bot.send_message(chat_id=self.chat_id, text=log_entry)


def main():
    load_dotenv()
    chat_id = os.getenv('TG_CHAT_ID')
    bot = telegram.Bot(token=os.getenv('TG_BOT_TOKEN'))
    logger.addHandler(TelegramLogsHandler(bot, chat_id))
    logger.info('Бот запущен')
    params = {}
    headers = {"Authorization": os.getenv('DVMN_API_TOKEN')}
    while True:
        try:
            response = requests.get(
                DVMN_LONG_POLLING_URL, headers=headers,
                params=params, timeout=91
            )
            response.raise_for_status()
            dvmn_review = response.json()
            if dvmn_review['status'] == 'timeout':
                params['timestamp'] = dvmn_review['timestamp_to_request']
            elif dvmn_review['status'] == 'found':
                attempt = dvmn_review['new_attempts'][0]
                send_message(bot, attempt, chat_id)
                params['timestamp'] = dvmn_review['last_attempt_timestamp']
        except ConnectionError as conn_err:
            print(conn_err, file=sys.stderr)
            time.sleep(3)
        except ReadTimeout:
            continue
        except Exception as err:
            logger.error('Бот упал с ошибкой:')
            logger.error(err, exc_info=True)


if __name__ == "__main__":
    logger.setLevel(logging.INFO)
    main()
