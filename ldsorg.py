import pdb
import os
import pickle
import logging
from time import sleep
import datetime
try:
    import ConfigParser as configparser
except ImportError:
    import configparser

import requests
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from dateutil.relativedelta import relativedelta

from callings import Membership
from email_markdown import Email, get_smtp

ENV_USERNAME = 'LDSORG_USERNAME'
ENV_PASSWORD = 'LDSORG_PASSWORD'

logger = logging.getLogger('lds.signin')


class LDSOrg(object):
    _URL_LOGIN = 'https://ident.lds.org/sso/UI/Login'
    ENDPOINT_URL = "https://tech.lds.org/mobile/ldstools/config.json"

    def __init__(self):
        """Create selenium and requests session."""
        self.loggedin = False
        self.driver = webdriver.PhantomJS()
        self.driver.set_window_size(900, 800)
        self.session = requests.Session()
        self.load_config_file()

    def load_config_file(self, file_name='config.cfg'):
        """Load config file

        [LDS.org]
        username = my-username
        password = my-password
        """
        self.config = configparser.ConfigParser()
        try:
            self.config.read(file_name)
        except Exception:
            pass

    def _get_login_creds(self):
        """Get username and password from environment.
        Returns:
            tuple (username, password)
        """
        username = os.getenv(ENV_USERNAME)
        password = os.getenv(ENV_PASSWORD)
        logger.info("Environment username={0:!r} "
                    "password=*{1[:-3]}".format(username, password))
        if username and password:
            return (username, password)

        if self.config.has_option('LDS.org', 'username'):
            username = self.config('LDS.org', 'username')
            password = self.config('LDS.org', 'password')

    def login(self, username=None, password=None, goto=None):
        """Log into lds.org

        At https://ident.lds.org/sso/UI/Login
        IDToken1 and IDToken2 are the username and password respectively.

        Args:
            username (str): the username
            password (str): the password
        """
        if username is None or password is None:
            username, password = self._get_login_creds()

        self.driver.get(self._URL_LOGIN)
        if len(self.driver.page_source) < 500:
            self.driver.get('https://ident.lds.org/sso/UI/Login')

        token1 = self.driver.find_element_by_id('IDToken1')
        token2 = self.driver.find_element_by_id('IDToken2')
        token1.send_keys(username)
        token2.send_keys(password)
        login_attempt = self.driver.find_element_by_xpath("//*[@type='submit']")
        login_attempt.submit()
        self.loggedin = True
        self._cookies_from_selenium_to_requests()
        self._get_endpoints()
        self._get_ward_information()

    def _cookies_from_selenium_to_requests(self):
        """Copy selenium cookies to requets.
        The login provides a number of needed cookies and request
        provides better and faster control over access of some URLs.
        """
        self.cookies = self.driver.get_cookies()
        for cookie in self.driver.get_cookies():
            c = {cookie['name']: cookie['value']}
            self.session.cookies.update(c)

    def _get_endpoints(self):
        """Get LDS provided endpoints.
        This dictionary of endpoints is a name and URL.  Some of these
        URLs need additional informantion, like the unit number.

        Attr:
            self.endpoints (dict): the endpoints
        """
        rv = self.session.get(self.ENDPOINT_URL)
        assert 200 == rv.status_code
        self.endpoints = rv.json()

    def _endpoint2url(self, endpoint):
        try:
            url = self.endpoints[endpoint]
        except AttributeError as err:
            self._get_endpoints()
            return self._endpoint2url(endpoint)

        if '%@' in url:
            url = url.replace('%@', self.unitNumber)
        return url

    def get_endpoint_data(self, endpoint):
        """Attempt to get the data by the LDS endpoint.

        Args:
            endpoint (str): labeled endpoint in LDS json.config
        Returns:
            The promised data, I hope.
        """
        url = self._endpoint2url(endpoint)
        rv = self.session.get(url)
        assert 200 == rv.status_code
        return rv.json()

    def _get_ward_information(self):
        """Get ward number, name, and stake name.

        Attr:
            self.unitNumber (str): ward unit number
            self.wardName (str): ward name
            self.stakeName (str): stake name
        """
        url = self._endpoint2url('current-user-unit')
        rv = self.session.get(url)
        assert 200 == rv.status_code
        self.unitNumber = rv.json()['message']

        url = self._endpoint2url('current-user-units')
        rv = self.session.get(url)
        assert 200 == rv.status_code
        data = rv.json()[0]
        for unit in data['wards']:
            if unit['usersHomeWard'] is True:
                self.wardName = unit['wardName']
                self.stakeName = unit['stakeName']
                break

    def get_membership(self, V2=False, use_archive=True):
        archive_name = "{0:%Y%m%d}-membership.pkl".format(self.today)
        if use_archive is True:
            try:
                with open(archive_name, 'rb') as filing:
                    data = pickle.load(filing)
            except Exception:
                return self.get_membership(V2=V2, use_archive=False)
            return Membership(data)

        endpoint = 'unit-members-and-callings'
        if V2:
            endpoint += '-v2'
        url = self._endpoint2url(endpoint)
        rv = self.session.get(url)
        assert 200 == rv.status_code
        data = rv.json()
        with open(archive_name, 'wb') as out:
            pickle.dump(data, out)
        return Membership(data)


class TempleRecommend(LDSOrg):
    _TARGET_URL = "https://www.lds.org/mls/mbr/services/recommend/recommend-status?lang=eng&unitNumber={0.unitNumber}"

    def __init__(self):
        super().__init__()
        self.today = datetime.date.today()

    def make_reports(self):
        TEMPLE_REPORT = 'Temple-Reports'
        options = self.config.items(TEMPLE_REPORT)
        self.report = {}
        # Get the names of all reports
        names = {_[0].split('_')[0] for _ in options}
        for name in names:
            title = self.config.get(TEMPLE_REPORT, name+'_title')
            head = self.config.getint(TEMPLE_REPORT, name+'_head')
            tail = self.config.getint(TEMPLE_REPORT, name+'_tail')
            head = self._relative_expire(head)
            tail = self._relative_expire(tail)
            rec = self._expire_in(head, tail)
            self.report[name] = self.markdown_report(rec, title)

    def markdown_report(self, recommends, title):
        """Create a markdown report

        Args:
            recommends (list): of recommends to include
            title (str): title of this report
        """
        headers= ('Name', 'Expire', 'Phone', 'Email')
        keys = ('name', 'formattedExpirationDate', 'phone', 'email')
        widths = [0] * len(headers)
        text = [title.title(), '='*len(title), '']
        # Get column widths
        for p in recommends:
            for idx, k in enumerate(keys):
                widths[idx] = max(widths[idx], len(p[k]))
        # Markdown table header
        text.append(' | '.join("{1:{0}s}".format(w, _)
                    for w, _ in zip(widths, headers)))
        text.append(' | '.join("-"*w for w in widths))
        # Markdown table body
        for p in recommends:
            fields = ["{0:{1}s}".format(p[k], w) for k, w in zip(keys, widths)]
            text.append(' | '.join(fields).rstrip())
        text.append('')
        return '\n'.join(text)


    def get_info(self, from_archive=True):
        """Get temple recommend information.

        Args:
            from_archive (bool): Get todays previously received info
        Returns:
            list of members information
            {
              age: years,
              birthDate: YYYYMMDD,
              birthDateSort: YYYYMMDD,
              email:
              endowmentDate: YYYYMMDD,
              expirationDate: YYYYMMDD,
              formattedEndowmentDate: 'DD Mmm YYYY',
              formattedExpirationDate: 'Mmm YYYY',
              formattedMrn: formatted membership number,
              genderLabelShort: F/M,
              id: individual number,
              marriageDate: None,
              mrn: unformated membership number,
              name: Last, first middle,
              nonMember: False,
              outOfUnitMember: False,
              phone: formatted phone number,
              recommendEditable: True,
              recommendStatus: ACTIVE,
              recommendStatusSimple: ACTIVE_EXPIRING_LATER,
              spokenName: First Middle Last,
              status: Active,
              type: REGULAR,
              unitName: Woodridge 1st Ward,
              unitNumber: 113638,
            }

        """
        archive_name = "{0:%Y%m%d}-temple.pkl".format(self.today)
        if from_archive is True:
            # Can we take from existing, fail gracefully
            try:
                with open(archive_name, 'rb') as json:
                    self.info = pickle.load(json)
                return self.info
            except Exception:
                pass

        # Get info from url
        rv = self.session.get(self._TARGET_URL.format(self))
        assert 200 == rv.status_code
        self.info = rv.json()

        # Save this stuff to an archive for later use
        with open(archive_name, 'wb') as out:
            pickle.dump(self.info, out)
        return self.info

    def _relative_expire(self, months=1):
        """Get the month relative to this month.

        Args:
            months (int): 1 is next month, -1 last month
        Returns:
            integer for use with ``expire_in()``
        """
        relative = self.today + relativedelta(months=months)
        return int("{0:%Y%m}".format(relative))

    def _expire_in(self, month, ending_month=None):
        """List members where recommend expires.

        Args:
            month (int or None): YYYYMM; if None, this month is used
            ending (int or None): YYYYMM; if None, only single month
        Returns:
            List of members ordered by expirationDate
        """
        members = []
        if month is None:
            month = int("{0:%Y%m}".format(self.today))
        if ending_month is None:
            ending_month = month
        assert ending_month >= month
        for member in self.info:
            try:
                expires = int(member['expirationDate'][:6])
            except:
                continue
            if month <= expires <= ending_month:
                members.append(member)
        members.sort(key=lambda x:x['expirationDate'])
        return members

    def send_email_to_bishopric(self, smtp, to_whom, bishopric):
        """Send email to bishop with his reports.

        Args:
            smtp (instance): smtplib.SMTP instance
            to_whom (str): either 'BISHOP', or 'COUNSELOR'
            bishopric (dict): from Membership.bishopric()
        Returns:
            Email for sending
        """
        SECTION = 'Temple'
        text = [self.config.get(SECTION, to_whom+'-MSG'), '']
        reports = self.config.get(SECTION, to_whom+'-Reports')
        if not reports:
            return None

        for report in reports.split(' '):
            text.append(self.report[report])

        params = {'From': self.config.get(SECTION, 'FROM_ADDR'),
                  'Subject': 'Temple recommend renewals'}

        if self.config.has_option(SECTION, 'BCC'):
            params['Bcc'] = self.config.get(SECTION, 'BCC')

        if to_whom == 'BISHOP':
            params['To'] = bishopric['bishop']['email']
            params['Subject'] = 'Temple recommends - Bishop'
        else:
            params['Cc'] = bishopric['bishop']['email']
            params['To'] = ', '.join((bishopric['counselor1']['email'],
                                      bishopric['counselor2']['email']))
        email = Email().make('\n'.join(text), **params)
        Email.send(email, smtp)


    def send_member_notices(self, smtp, bishopric):
        """Send email to members about expiring recommends.

        Args:
            smpt (instance): smtplib.SMTP instance
            bishopric (instance): Membership.bishopric()
        """
        SECTION = 'Temple'
        head = self.config.getint(SECTION, 'MEMBER_head')
        tail = self.config.getint(SECTION, 'MEMBER_tail')
        head = self._relative_expire(head)
        tail = self._relative_expire(tail)
        rec = self._expire_in(head, tail)

        bcc = list({_['email'] for _ in rec if _['email']})
        if self.config.has_option(SECTION, 'BCC'):
            bcc.append(self.config.get(SECTION, 'BCC'))

        with open(self.config.get(SECTION, 'MEMBER'), 'rt') as info:
            body = info.read()
        body = body.format(**bishopric)

        from_ = self.config.get(SECTION, 'FROM_ADDR')
        to_ = email.utils.formataddr('undisclosed-recipients',
                                     email.utils.parseaddr(from_)[-1])
        params = {'From': from_, 'To': to_,
                  'Subject': 'Your temple recommend will expire soon',
                  }
        email = Email().make(body, **params)
        smtp.sendmail(params['From'], bcc, email.as_string())


def preferred_to_spoken(name):
    parts = name.split(',')
    return ' '.join(reversed(parts))


if __name__ == "__main__":

    req = TempleRecommend()
    req.login()
    req.get_info()

    member = req.get_membership()
    bishopric = member.bishopric()
    bishopric['wardName'] = req.wardName

    smtp = get_smtp('config.cfg')

    req.make_reports()
    req.send_email_to_bishopric(smtp, 'BISHOP', bishopric)
    req.send_email_to_bishopric(smtp, 'COUNSELOR', bishopric)
    sleep(5)
    req.send_member_notices(smtp, bishopric)
