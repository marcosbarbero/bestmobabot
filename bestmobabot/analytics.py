import requests

from bestmobabot.logger import logger

URL = 'https://www.google-analytics.com/collect'
TID = 'UA-65034198-7'
CID = '555'

session = requests.Session()


def send_event(*, category: str, action: str, user_id: str):
    try:
        with session.post(URL, data={'v': 1, 'tid': TID, 'cid': CID, 't': 'event', 'ec': category, 'ea': action, 'uid': user_id}) as response:
            response.raise_for_status()
    except Exception as ex:
        logger.warning('😱 Failed to send the event.', exc_info=ex)


def send_exception(*, description: str, user_id: str):
    try:
        with session.post(URL, data={'v': 1, 'tid': TID, 'cid': CID, 't': 'exception', 'exd': description, 'exf': '1', 'uid': user_id}) as response:
            response.raise_for_status()
    except Exception as ex:
        logger.warning('😱 Failed to send the exception.', exc_info=ex)
