# coding: utf8
"""
-------------------------------------------------------
Config Example
-------------------------------------------------------
"""
import pdb
import os
import sys
import codecs
import pprint
import calendar
import datetime
from textwrap import dedent, wrap
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.utils import COMMASPACE, formataddr
import smtplib
try:
    import lds_org
except ImportError:
    print("Be sure to use import needed requirements:")
    print("  lds_org, markdown, and lxml")
    sys.exit(1)
import markdown
from lxml.html import fromstring


BASEDIR = os.path.dirname(__file__)
RECOMMEND_URL = "https://www.lds.org/mls/mbr/recommend/recommend-status?lang=eng&unitNumber=%@"

def date_from_8(date):
    """YYYYMM00 to 'YYYY Month'
    """
    try:
        year = int(date[:4])
    except ValueError:
        return 'Unknown'
    month = int(date[4:6])
    day = calendar.monthrange(year, month)[-1]
    return datetime.date(year, month, day).strftime("%B %Y")

def expired_and_expiring(lds=None, html=None):
    """Scrape recommend information from web report

    Return a dictionary with a list of the individuals
    {Group:
        [{data-spoken_name:
          href: URL to see person on LDS.org
          expires: YYYYMM00 or None
          data-email: email address or empty ''
          data-phone: phone number or empty ''
         }, ...]
    }
    """
    people = {}
    if html is None:
        if lds is None and html is None:
            with lds_org.session as lds:
                rv = lds.get(RECOMMEND_URL)
                html = rv.text
        elif lds:
            rv = lds.get(RECOMMEND_URL)
            html = rv.text

        with open('html.html', 'wt') as out:
            out.write(html)

    doc = fromstring(html)
    recommends = "//table[@id='dataTable']/tbody/tr"
    data_keys = ('href', 'data-spoken-name', 'data-email', 'data-phone')
    for tr in doc.xpath(recommends):
        status = tr.xpath("td[2]")[0].text.strip()
        if status == 'ACTIVE':
            continue
        a = tr.xpath("td[@class='n fn']/a")[0]
        data = dict(a.items())
        data_email = data['data-email']
        person = {k:v for k,v in a.items() if k in data_keys}
        expired = tr.xpath("td[6]")[0].text.strip()
        person['expires'] = expired
        person['month'] = date_from_8(person['expires'])
        person['link'] = "[{0[data-spoken-name]}](https://lds.org{0[href]})"\
                            .format(person)
        person['email'] = '' if not data_email else "<{}>".format(data_email)
        people.setdefault(status, []).append(person)
    return people

def markdown_report( group, linkable=True):
    headers= ('Name', 'Expire', 'Phone', 'Email')
    keys = ('link', 'month', 'data-phone', 'email')
    widths = [0] * len(headers)
    text = []
    # Get column widths
    for p in group:
        for idx, k in enumerate(keys):
            widths[idx] = max(widths[idx], len(p[k]))
    # Markdown table header
    text.append(' | '.join("{1:{0}s}".format(w, _)
                for w, _ in zip(widths, headers)))
    text.append(' | '.join("-"*w for w in widths))
    # Markdown table body
    for p in group:
        fields = ["{0:{1}s}".format(p[k], w) for k, w in zip(keys, widths)]
        text.append(' | '.join(fields).rstrip())
    text.append('')
    return '\n'.join(text)


class Email(object):

    def __init__(self, reports):
        self.reports = reports

    def title(self, k):
        title = k.replace('_', ' ').title()
        return [title, '-' * len(title), '']

    def preferred(self, lds_preferred):
        parts = [_.strip() for _ in lds_preferred.split(',')]
        return ' '.join(parts)

    def para(self, append_to, text):
        append_to.extend(wrap(dedent(text).lstrip()))
        append_to.append('')

    def make(self, **kwargs):
        msg = MIMEMultipart()
        body = self.body()

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
        for k, v in kwargs.items():
            msg[k] = v
        return msg

    @staticmethod
    def send(email, smtp):
        to_addrs = email['To'].split(COMMASPACE)
        if 'Cc' in email:
            to_addrs.extend(email['Cc'].split(COMMASPACE))
        if 'Bcc' in email:
            to_addrs.extend(email['Bcc'].split(COMMASPACE))
            del email['Bcc']

        print("Subject: {0[Subject]}\nTo: {0[To]}\nBcc:"
              "{0[Bcc]}\n{1}\n".format(email, to_addrs))
        return smtp.sendmail(email['From'], to_addrs, email.as_string())

class Counselor(Email):
    def body(self):
        text = []
#        self.para(text, """
#            Per our discussion in bishopric meeting last Sunday, I have
#            created this as an example of an email you would get at the
#            beginning of each month.  The Bishop also receives this along
#            with the list of expired recommends. All this information is
#            already on LDS.org the only difference is this pushes the
#            information to your email at the beginning of each month.
#            The computer will automate this.""")
        for k in ('EXPIRING_THIS_MONTH', 'EXPIRING_NEXT_MONTH'):
            text.extend(self.title(k))
            text.append(self.reports[k])
        return '\n'.join(text)


class Bishop(Email):
    def body(self):
        counselor_rpts = ('EXPIRING_THIS_MONTH', 'EXPIRING_NEXT_MONTH')
        text = []
#        self.para(text, """
#            Bishop,
#
#            Per our discussion in bishopric meeting last Sunday, I have
#            created this email as an example of an email you would get
#            at the beginning of each month.
#            Counselors will get a similar email but without the expired
#            list.  This information is already on LDS.org, this just
#            pushes the information to your email at the beginning of
#            each month.  The computer will automate this.""")
        self.para(text, """
            The following two reports were sent to your councelors.""")
        for k in counselor_rpts:
            if k in self.reports:
                text.extend(self.title(k))
                text.append(self.reports[k])

        for k, report in sorted(self.reports.items()):
            if k in counselor_rpts:
                continue
            text.extend(self.title(k))
            text.append(self.reports[k])
            text.append('- ' * 30)

        return '\n'.join(text)


class SMTPStdout(object):
    def sendmail(self, from_addr, to_addrs, msg):
        print("-"*60)
        print(msg.split('\n\n')[0])
        print(to_addrs)

    def quit(self):
        return True


def get_smtp(config):
    pdb.set_trace()
    if config.has_option('Testing', 'STDOUT_SERVER') and config.getboolean('Testing', 'STDOUT_SERVER'):
        return SMTPStdout()

    domain = config.get('SMTP', 'DOMAIN')
    if not domain:
        return SMTPStdout()

    domain = config.get('SMTP', 'DOMAIN').split(':')
    params = {}
    if len(domain) > 1:
        params['port'] = int(domain[1])

    server = smtplib.SMTP(domain[0], **params)
    if config.getboolean('SMTP', 'TLS'):
        server.starttls()
    server.login(config.get('SMTP', 'USERNAME'),
                    config.get('SMTP', 'PASSWORD'))
    return server

def ward_stake_name(lds):
    """Get the ward name and the stake name for the current user."""
    rv = lds.get('current-user-units')
    assert rv.status_code == 200
    data = rv.json()[0]
    for unit in data['wards']:
        if unit['wardUnitNo'] == int(lds.unitNo):
            return unit['wardName'], unit['stakeName']


def dump_cookies(fetcher, filename):
    with open(filename, 'wt') as out:
        out.write(pprint.pformat(fetcher.cookies.get_dict()))


if __name__ == "__main__":
    import argparse
    from callings import Membership
    try:
        import ConfigParser as configparser
    except ImportError:
        import configparser

    parser = argparse.ArgumentParser()
    parser.add_argument('config', help='configuration file')
    parser.add_argument('--no-email', help='absolutely no email')
    parser.add_argument('--html', help='Test parsing of html file')
    args = parser.parse_args()

    if args.html:
        html = open(args.html, 'rt').read()
        pdb.set_trace()
        d = expired_and_expiring(None, html)
        print(d)
        sys.exit(0)

    config = configparser.ConfigParser()
    config.read(args.config)

    server = None if args.no_email else get_smtp(config)
    ldsorg = lds_org.LDSOrg(config.get('LDS.org', 'username'),
                            config.get('LDS.org', 'password'), signin=True)
    dump_cookies(ldsorg, '01-after-signin.txt')
    wardName, stakeName = ward_stake_name(ldsorg)
    dump_cookies(ldsorg, '02-after-ward-stake.txt')
#    membership = Membership()
#    membership.get(ldsorg)
    groups = expired_and_expiring(ldsorg)
    sys.exit(0)
    bishopric = membership.bishopric()

    reports = {}
    for k, group in groups.items():
        if k == 'EXPIRED_OVER_3_MONTHS':
            # Sort these so the most recent ones are first.
            group = sorted(group, key=lambda x: x['expires'], reverse=True)
        rpt = markdown_report(group)
        reports[k] = rpt

    params = {'From': config.get('Email', 'FROM_ADDR')}
    for key, sect, opt in (('To', 'Testing', 'TO_ADDR'),
                           ('Bcc', 'Email', 'BCC_ADDR')):
        if config.has_option(sect, opt):
            params[key] = config.get(sect, opt)

    config_send = lambda s,n: config.has_option(s,n) and config.getboolean(s,n)

    if config_send('Email', 'COUNSELOR'):
        params['Subject'] = 'Temple recommend renewal'
        if 'To' not in params:
            params['Cc'] = bishopric['bishop']['email']
            params['To'] = COMMASPACE.join((bishopric['counselor1']['email'],
                                            bishopric['counselor2']['email']))
        email = Counselor(reports).make(**params)
    #    Email.send(email, server)

    if config_send('Email', 'BISHOP'):
        params['Subject'] = 'Temple recommends expired'
        if 'To' not in params:
            params['To'] = COMMASPACE.join((bishopric['bishop']['email'],
                                            bishopric['exec_sec']['email']))
        email = Bishop(reports).make(**params)
    #    Email.send(email, server)


    params = dict(wardName=wardName, stakeName=stakeName)
    params.update(bishopric)
    for k, group in groups.items():
        if not config.has_option('Email', k):
            continue
        md = open(os.path.join(BASEDIR, config.get('Email', k)), 'rt').read()
        body = md.format(**params)
        body = markdown.markdown(body, ['markdown.extensions.smarty',
                                        'markdown.extensions.tables'])
        msg = MIMEText(body.encode('utf-8'), 'html', _charset='utf-8')
        addr = config.get('Email', 'FROM_ADDR')
        msg['Subject'] = "Temple recommend " + k.replace('_',' ').lower()
        msg['From'] = addr
        msg['To'] = 'Undisclosed recipents <' + addr.split('<')[-1]

        to_addrs = [_['data-email'] for _ in group if _['data-email']]
        if config.has_option('Testing', 'TO_ADDR'):
            to_addrs = config.get('Testing', 'TO_ADDR').split(COMMASPACE)
        if config.has_option('Email', 'BCC_ADDR'):
            to_addrs.append(config.get('Email', 'BCC_ADDR'))
        if not to_addrs:
            continue
        print("Subject: {0[Subject]}\nTo: {0[To]}\n{1}\n"
              .format(msg, to_addrs))
    #    server.sendmail(msg['From'], to_addrs, msg.as_string())

    server.quit()
