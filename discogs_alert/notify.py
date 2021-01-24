import json
import os
import requests


__all__ = ['send_pushbullet_push']


def send_pushbullet_push(message_body, message_title):
    """

    @param message_body
    @param message_title
    :return:
    """

    message = {"type": "note", "title": message_title, "body": message_body}
    headers = {'Authorization': 'Bearer ' + os.getenv("PUSHBULLET_TOKEN"), 'Content-Type': 'application/json'}
    resp = requests.post('https://api.pushbullet.com/v2/pushes', data=json.dumps(message), headers=headers)
    if resp.status_code != 200:
        print("ERROR")
        return False
    else:
        return True
