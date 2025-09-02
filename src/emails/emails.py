import json
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from typing import Literal, Sequence

from src.config import project_config
from src.log.log import logger


def get_email_addresses(emails_type: Literal['gmails', 'sah_mails']) -> Sequence[str]:
    """чтение файла с почтовыми адресами
    """
    path = Path(__file__).resolve().parent.parent.parent / 'conf/emails.json'
    with open(path, 'r') as f:
        data = json.load(f)

        emails = []
        emails.extend(data[emails_type])
        return emails


class EmailSender:
    def __init__(self, receiver_emails: Sequence[str]) -> None:
        self._sender_email = project_config.config.get('email', 'sender_email')
        self._password = project_config.config.get('email', 'password')
        self._smtp_server = project_config.config.get('email', 'smtp_server')
        self._smtp_port = project_config.config.get('email', 'smtp_port')
        self.to_addresses = receiver_emails

    def _create_message(self, subj_txt: str, mess_txt: str):
        """ Создание письма """
        message = MIMEMultipart()
        message['From'] = self._sender_email
        message['To'] = ', '.join(self.to_addresses)
        message['Subject'] = subj_txt
        message.attach(MIMEText(mess_txt, 'plain'))
        return message

    def send_message(self, subj_txt: str, mess_txt: str):
        """ Отправка письма """
        message = self._create_message(subj_txt, mess_txt)
        try:
            with smtplib.SMTP(self._smtp_server, self._smtp_port) as smtp:
                smtp.starttls()
                smtp.login(self._sender_email, self._password)
                smtp.sendmail(self._sender_email, self.to_addresses, message.as_string())
            logger.info(f'Письмо {subj_txt} отправлено!')
        except Exception as e:
            logger.error(e)


def send_email(subj_txt: str, mess_txt: str) -> None:
    recipients = get_email_addresses('sah_mails')
    es = EmailSender(recipients)
    es.send_message(subj_txt, mess_txt)
