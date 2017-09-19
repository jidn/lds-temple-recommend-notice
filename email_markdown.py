# coding: utf8
from textwrap import dedent, wrap
try:
    import ConfigParser as configparser
except ImportError:
    import configparser
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import smtplib
import markdown


class Email(object):
    """Created and send emails."""
    def title(self, title):
        return [title.title(), '-' * len(title), '']

    def preferred(self, lds_preferred):
        parts = [_.strip() for _ in lds_preferred.split(',')]
        return ' '.join(parts)

    def para(self, append_to, text):
        append_to.extend(wrap(dedent(text).lstrip()))
        append_to.append('')

    def make(self, body, **kwargs):
        """Make HTML email with text version."""
        msg = MIMEMultipart('alternative')
        for k, v in kwargs.items():
            msg[k] = v

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


class SMTPStdout(object):
    is_dummy = True

    def sendmail(self, from_addr, to_addrs, msg):
        print("-"*60)
        print(msg.split('\n\n')[0])
        print(to_addrs)

    def quit(self):
        return True


def get_smtp(config_file, section='SMTP'):
    """Get SMTP information from a config file.

    SMTP section in the config file looks like:
    [SMTP]
    DOMAIN = smtp.gmail.com:587
    USERNAME = my-username
    PASSWORD = my-password
    TLS = True

    Use your domain, username, and password.  This is showing the values
    for gmail.  Without a domain, it will just print to stdout.

    Args:
        config_file (str): filename
        section (str): section in config_file, default "SMTP"

    Returns:
        smtplib.SMTP object
    """
    config = configparser.ConfigParser()
    config.read(config_file)
    domain = config.get(section, 'DOMAIN')
    if not domain:
        return SMTPStdout()

    domain = domain.split(':')
    params = {}
    if len(domain) > 1:
        params['port'] = int(domain[1])

    server = smtplib.SMTP(domain[0], **params)
    if config.has_option(section, 'TLS') and config.getboolean(section, 'TLS'):
        server.starttls()

    server.login(config.get(section, 'USERNAME'),
                 config.get(section, 'PASSWORD'))
    return server
