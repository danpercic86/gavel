import base64
import csv
import email
import email.mime.multipart
import email.mime.text
import io
import json
import os
import re
import smtplib
from functools import wraps

import markdown
import requests
from flask import Markup, Response, request, render_template, session, abort

import gavel.constants as constants
import gavel.settings as settings
from gavel import celery


def gen_secret(length):
    return base64.b32encode(os.urandom(length))[:length].decode("utf8").lower()


def authenticate():
    return Response(
        "Access denied.", 401, {"WWW-Authenticate": 'Basic realm="Login Required"'}
    )


def check_auth():
    api_key = request.args.get("key", "")
    if api_key:
        return api_key == settings.API_KEY

    auth = request.authorization
    if auth:
        token = session.pop("_csrf_token", None)
        if request.method not in ("GET", "HEAD", "OPTIONS"):
            if not token or token != request.form.get("_csrf_token"):
                abort(403)
        return auth.username == "admin" and auth.password == settings.ADMIN_PASSWORD

    auth_header = request.headers.get("Authorization", None)
    if auth_header:
        try:
            auth_type, api_key = auth_header.split(None, 1)
            auth_type = auth_type.lower()
        except ValueError:
            return False

        return auth_type == "key" and api_key == settings.API_KEY

    return False


def requires_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not check_auth():
            return authenticate()
        return f(*args, **kwargs)

    return decorated


def data_to_csv_string(data):
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerows(data)
    return output.getvalue()


def data_from_csv_string(string):
    data_input = io.StringIO(string)
    reader = csv.reader(data_input)
    return list(reader)


def get_paragraphs(message):
    paragraphs = re.split(r"\n\n+", message)
    paragraphs = [i.replace("\n", "<br>") for i in paragraphs if i]
    return paragraphs


@celery.task
def send_emails(emails):
    """
    Send a batch of emails.

    This function takes a list [(to_address, subject, body)].
    """

    if settings.EMAIL_AUTH_MODE == "tls":
        server = smtplib.SMTP(settings.EMAIL_HOST, settings.EMAIL_PORT)
        server.ehlo()
        server.starttls()
        server.ehlo()
    elif settings.EMAIL_AUTH_MODE == "ssl":
        server = smtplib.SMTP_SSL(settings.EMAIL_HOST, settings.EMAIL_PORT)
    elif settings.EMAIL_AUTH_MODE == "none":
        server = smtplib.SMTP(settings.EMAIL_HOST, settings.EMAIL_PORT)
        server.ehlo()
    else:
        raise ValueError("unsupported auth mode: %s" % settings.EMAIL_AUTH_MODE)

    server.login(settings.EMAIL_USER, settings.EMAIL_PASSWORD)

    exceptions = []
    for e in emails:
        try:
            to_address, subject, body = e
            msg = email.mime.multipart.MIMEMultipart()
            msg["From"] = settings.EMAIL_FROM
            msg["To"] = to_address
            recipients = [to_address]
            if settings.EMAIL_CC:
                msg["Cc"] = ", ".join(settings.EMAIL_CC)
                recipients.extend(settings.EMAIL_CC)
            msg["Subject"] = subject
            msg.attach(email.mime.text.MIMEText(body, "plain"))
            server.sendmail(settings.EMAIL_FROM, recipients, msg.as_string())
        except Exception as e:
            exceptions.append(e)  # XXX is there a cleaner way to handle this?

    server.quit()
    if exceptions:
        raise Exception("Error sending some emails: %s" % exceptions)


def send_sendgrid_emails(emails):
    exceptions = []
    for email in emails:
        to_address, subject, body = email
        response = sendgrid_send_email(to_address, subject, body)
        print(response)
        if not (
            response.status_code == requests.codes.ok
            or response.status_code == requests.codes.accepted
        ):
            all_errors = [
                error_obj["message"] for error_obj in response.json()["errors"]
            ]
            error_msg = "%s (error %s)" % (to_address, str(all_errors))
            exceptions.append(error_msg)
    if exceptions:
        raise Exception("Error sending some emails: %s" % exceptions)


def sendgrid_send_email(to_address, subject, body):
    payload = {
        "personalizations": [{"to": [{"email": to_address}], "subject": subject}],
        "from": {"email": settings.EMAIL_FROM},
        "subject": subject,
        "content": [{"type": "text/html", "value": body}],
    }
    headers = {
        "authorization": "Bearer %s" % settings.SENDGRID_API_KEY,
        "content-type": "application/json",
    }

    response = requests.request(
        "POST", constants.SENDGRID_URL, data=json.dumps(payload), headers=headers
    )
    return response


def render_markdown(content):
    return Markup(markdown.markdown(content))


def user_error(message):
    return render_template("error.html", message=message), 400


def server_error(message):
    return render_template("error.html", message=message), 500


def cast_row(row):
    """
    Convert workbook sheet cells into integers if they are equal to integer
    values and convert everything to a string.

    The xlrd library seems to import cells as float values if the cell had a
    numeric value, so this method is needed to correct that.
    """
    for i, item in enumerate(row):
        if isinstance(item, (float, int)) and int(item) == item:
            row[i] = str(int(item))
        else:
            row[i] = str(item)
    return row
