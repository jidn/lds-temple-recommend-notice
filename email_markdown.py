# coding: utf8
import pdb
import os
import sys
import pprint
import calendar
import datetime
from textwrap import dedent, wrap
try:
    import ConfigParser as configparser
except ImportError:
    import configparser
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import email.utils
import smtplib
import markdown

COMMASPACE = email.utils.COMMASPACE


class Email(object):

    def title(self, title):
        return [title.title(), '-' * len(title), '']

    def preferred(self, lds_preferred):
        parts = [_.strip() for _ in lds_preferred.split(',')]
        return ' '.join(parts)

    def para(self, append_to, text):
        append_to.extend(wrap(dedent(text).lstrip()))
        append_to.append('')

    def make(self, body, **kwargs):
        msg = MIMEMultipart('alternative')
        for k, v in kwargs.items():
            msg[k] = v
        msg['Date'] = email.utils.formatdate()
        # msg['Message-ID'] = email.utils.make_msgid(msg['Date'])
        # It creates a localhost msgid which spamassassin ranks higher
        # than not having it at all.

        msg.attach(MIMEText(body, 'text'))

        body = markdown.markdown(body, ['markdown.extensions.tables',
                                        'markdown.extensions.smarty'])
        html = dedent("""
            <html><head>
            <style type='text/css'>
            h2 { font-size: 150%% }
            table { border-collapse: collapse }
            th {text-align: center}
            td {padding-left:1em }
            tbody tr:nth-child(odd) { background: #eee; }
            tbody tr:hover { background: yellow; }
            </style></head><body>
            %s
            </body></html>""").strip() % body
        msg.attach(MIMEText(html, 'html'))
        return msg

    @staticmethod
    def send(email, smtp):
        to_addrs = email['To'].split(COMMASPACE)
        if 'Cc' in email:
            to_addrs.extend(email['Cc'].split(COMMASPACE))
        if 'Bcc' in email:
            to_addrs.extend(email['Bcc'].split(COMMASPACE))
            del email['Bcc']

        print("Subject: {0[Subject]}\nTo: {0[To]}\n"
              "{1}\n".format(email, to_addrs))
        print(email.as_string())
        return smtp.sendmail(email['From'], to_addrs, email.as_string())


class SMTPStdout(object):
    is_dummy = True

    def sendmail(self, from_addr, to_addrs, msg):
        print("-"*60)
        print(msg.split('\n\n')[0])
        print(to_addrs)

    def quit(self):
        return True


def get_smtp(config_file):
    """Get SMTP information from a config file.

    SMTP section in the config file looks like:
    [SMTP]
    DOMAIN = smtp.gmail.com:587
    USERNAME = my-username
    PASSWORD = my-password
    TLS = True

    Use your domain, username, and password.  This is showing the values
    for gmail.  Without a domain, it will just print to stdout.
    """
    config = configparser.ConfigParser()
    config.read(config_file)
    domain = config.get('SMTP', 'DOMAIN')
    if not domain:
        return SMTPStdout()

    domain = config.get('SMTP', 'DOMAIN').split(':')
    params = {}
    if len(domain) > 1:
        params['port'] = int(domain[1])

    server = smtplib.SMTP(domain[0], **params)
    if config.has_option('SMTP', 'TLS') and config.getboolean('SMTP', 'TLS'):
        server.starttls()

    server.login(config.get('SMTP', 'USERNAME'),
                    config.get('SMTP', 'PASSWORD'))
    return server
