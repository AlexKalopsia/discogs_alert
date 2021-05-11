from email.message import EmailMessage
import json
import requests
import smtplib

__all__ = ['send_pushbullet_push', 'send_email']


def send_pushbullet_push(token, message_title, message_body, verbose=False):
    """ Sends notification of found record via pushbullet.

    @param token: (str) pushbullet token needed to send notification to correct user
    @param message_title: (str) title of message
    @param message_body: (str) body of the message
    @param verbose: (bool) boolean indicating whether to print stuff
    :return: True if successful, False otherwise.
    """

    try:
        headers = {'Authorization': 'Bearer ' +
                   token, 'Content-Type': 'application/json'}
        message = {"type": "note",
                   "title": message_title, "body": message_body}
        url = 'https://api.pushbullet.com/v2/pushes'

        # work out if there is an existing, identical push
        resp = requests.get(url, headers=headers)
        have_already_sent = False
        for p in resp.json().get('pushes'):
            if p.get('title') == message.get('title') and p.get('body') == message.get('body'):
                have_already_sent = True
                break

        # if not, send one
        if not have_already_sent:
            if verbose:
                print("sending notification")
            resp = requests.post(
                url, data=json.dumps(message), headers=headers)
            if resp.status_code != 200:
                print(
                    f"error {resp.status_code} sending pushbullet notification: {resp.content}")
                return False
            else:
                return True
        return True
    except Exception as e:
        print(f"Exception sending pushbullet push: {e}")
        return False


def send_email(email_server_smtp, email_server_port, email_from, email_password, email_to, title, body):
    server = smtplib.SMTP(email_server_smtp, email_server_port)
    server.ehlo()
    server.starttls()
    server.ehlo()
    server.login(email_from, email_password)
    print('sending email')

    msg = EmailMessage()
    msg['Subject'] = title
    msg['From'] = email_from
    msg['To'] = email_to
    msg.set_content(body)
    print('email sent')
    server.quit()
