"""Send email notices to bishopric and members on expiring recommends.
"""
import pdb
import datetime
import collections
from email.mime.text import MIMEText
try:
    import ConfigParser as configparser
except ImportError:
    import configparser
try:
    from future_builtins import filter, map
except ImportError:
    pass
import lds_org
import email_markdown
from dateutil import relativedelta


__version__ = "1.0rc1"
BISHOPRIC = {'Bishop': 'bishop',
             'Bishopric First Counselor': 'counselor1',
             'Bishopric Second Counselor': 'counselor2',
             'Ward Executive Secretary': 'exec_sec',
             'Ward Clerk': 'ward_clerk'}

def find_yyyymm(months, today=None):
    """Get the month relative to this month.

    Args:
        months (int): 1 is next month, -1 last month
        today (datetime.date): if None use datetime.date.today()

    Returns: (int)
        YYYYMM

    >>> find_yyyymm(0, datetime.date(2017, 9, 4))
    '201709'
    >>> find_yyyymm(-1, datetime.date(2017, 3, 30))
    '201702'
    """
    if today is None:
        today = datetime.date.today()
    relative = today + relativedelta.relativedelta(months=months)
    return str(relative.year * 100 + relative.month)


class PeopleAdapter(lds_org.DataAdapter):
    """Adapts recommend data.

    >>> PeopleAdapter({'phone': '555-3315'}).phone
    '555-3315'
    >>> PeopleAdapter(dict(phone='', householdPhone='5551234')).phone
    '5551234'
    >>> PeopleAdapter({'email': 'a@_.com'}).email
    'a@_.com'
    >>> PeopleAdapter(dict(email='', householdEmail='a@_.com')).email
    'a@_.com'
    >>> PeopleAdapter({'name': 'Doe, John'}).surname
    'Doe'
    """

    @property
    def phone(self):
        return self._data['phone'] or self.householdPhone

    @property
    def email(self):
        return self._data['email'] or self.householdEmail

    @property
    def surname(self):
        try:
            return self._data['surname']
        except KeyError:
            # Needed for callings
            return self._data['name'].split(',')[0].strip()

    def __repr__(self):
        return "<PeopleAdapter.name=%s>" % self.name


class RecommendGroup(object):
    """Create recommend reports from config file."""

    def __init__(self, config_file='config.cfg'):
        self.groups = {}
        self.report = {}
        self.get_config_info(file_name=config_file)

    def get_config_info(self, file_name, section='Reports'):
        """Load config file

        [Reports]
        x_title = Expire this month
        x_head = 0
        x_tail = 0

        y_title = Expire next month
        y_head = 1
        y_tail = 1

        z_title = Expired in last 3 months
        z_head = -3
        z_tail = -1

        Args:
            file_name (str): the INI filename
            section (str): the INI section name

        Side effects:
            self.config (configparser)
        """
        self.config = configparser.ConfigParser()
        self.config.read(file_name)
        options = self.config.items(section)
        self.groups = {}
        # Get the names of all reports
        names = {_[0].split('_')[0] for _ in options}
        today = datetime.date.today()
        for name in names:
            head = self.config.getint(section, name + '_head')
            tail = self.config.getint(section, name + '_tail')
            head = find_yyyymm(head, today)
            tail = find_yyyymm(tail, today)
            func = lambda v, h=head, t=tail: h <= v <= t
            self.groups[name] = [func, self.config.get(section, name + '_title')]

    def select_recommends(self, recommends):
        """Create exipiring reports for a sequence of recomends.

        Args:
            recommends (list[dict]): long list of recomment holders

        Side effects:
            self.report (dict): Create text reports, one for each of
                the criteria in config.
        """
        selected = collections.defaultdict(list)
        for recommend in recommends:
            try:
                expire_date = recommend['expirationDate'][:6]
            except TypeError:
                expire_date = '000000'
            for k, v in self.groups.items():
                if v[0](expire_date):
                    #print(k, expire_date, recommend['name'])
                    selected[k].append(PeopleAdapter(recommend))
        self.report = {}
        for k, v in selected.items():
            v.sort(key=lambda x: x.name)
            title = self.groups[k][-1]
            self.report[k] = self.table(v)

    def table(self, recommends):
        """Create markdown tables.

        Args:
            recommends (iterable): of recommends to include

        Returns: (str)
            A table of Name | Phone | Email
        """

        headers = ('Name', 'Expires', 'Phone', 'Email')
        keys = ('name', 'expire', 'phone', 'email')
        widths = [len(_) for _ in headers]
        text = []
        # Get column widths
        for p in recommends:
            date = p.expirationDate
            p._data['expire'] = "{}-{}".format(date[:4], date[4:6])
            for idx, k in enumerate(keys):
                widths[idx] = max(widths[idx], len(getattr(p, k)))
        # Markdown table header
        text.append(' | '.join("{1:{0}s}".format(w, _)
                               for w, _ in zip(widths, headers)))
        text.append(' | '.join("-"*w for w in widths))
        # Markdown table body
        for p in recommends:
            fields = ["{0:{1}s}".format(getattr(p, k), w)
                      for k, w in zip(keys, widths)]
            text.append(' | '.join(fields).rstrip())
        text.append('')
        return '\n'.join(text)

    def send_email_to_bishopric(self, smtp, to_whom, bishopric, test=False):
        """Send email to bishop with his reports.

        Args:
            smtp (instance): smtplib.SMTP instance
            to_whom (str): either 'BISHOP', or 'COUNSELOR'
            bishopric (dict): from Membership.bishopric()
            test (boolean): send email only to BCC-ADDR
        Returns:
            Email for sending
        """
        section = 'Email'
        text = [self.config.get(section, to_whom+'-MSG'), '']
        reports = self.config.get(section, to_whom+'-REPORTS')
        if not reports:
            return None

        for report in reports.split(' '):
            title = self.groups[report][-1]
            text.extend([title, '=' * len(title)])
            text.append(self.report[report])

        params = {'From': self.config.get(section, 'FROM-ADDR')}

        if to_whom == 'BISHOP':
            params['Subject'] = 'Temple recommends - Bishop'
            params['To'] = (bishopric['bishop'].email,)
        elif to_whom == 'COUNSELOR':
            params['Subject'] = 'Temple recommend renewals'
            params['To'] = [bishopric[_].email for _ in ('counselor1',
                                                         'counselor2')]
            params['Cc'] = (bishopric['bishop'].email,)

        if self.config.has_option(section, 'BCC-ADDR'):
            params['Bcc'] = (self.config.get(section, 'BCC-ADDR'),)

        to_addr = set()
        for group in ('To', 'Cc', 'Bcc'):
            addrs = params.get(group, tuple())
            if not addrs:
                continue
            to_addr.update(set(addrs))
            params[group] = ', '.join(addrs)
        if test:
            to_addr = [self.config.get(section, 'BCC-ADDR')]
        email_msg = email_markdown.Email().make('\n'.join(text), **params)
        pdb.set_trace()
        smtp.sendmail(params['From'], to_addr, email_msg.as_string())


    def send_member_notices(self, smtp, bishopric, recommends, test=False):
        """Send email to members about expiring recommends.

        Args:
            smpt (instance): smtplib.SMTP instance
            bishopric (instance): Membership.bishopric()
            recommends (list): series of recommends
            test (boolean): send email only to BCC-ADDR
        """
        section = 'Email'
        body = self.config.get(section, 'MEMBER-MSG')
        body = body.format(**bishopric)

        bcc = set()
        start, end = tuple(find_yyyymm(self.config.getint(section, x))
                           for x in ('MEMBER-HEAD', 'MEMBER-TAIL'))
        logger = ['Looking for members to notify.']
        for recommend in recommends:
            try:
                expire_date = recommend['expirationDate'][:6]
            except TypeError:
                expire_date = '000000'
            if start <= expire_date <= end:
                addr = recommend['email'] or recommend['householdEmail']
                if addr:
                    logger.append('{0[name]} {1}'.format(recommend, addr))
                    bcc.add(addr)
                else:
                    logger.append('{0[name]} missing email.'.format(recommend))

        from_addr = self.config.get(section, 'FROM-ADDR')
        if not test:
            email_msg = email_markdown.Email().make(body,
                        From=from_addr, To='undisclosed-recipients',
                        Subject='Your temple recommend will expire soon')
            pdb.set_trace()
            err = smtp.sendmail(from_addr, list(bcc), email_msg.as_string())
            if err:
                logger.append("Errors with %s" % str(err))

        logger.append("\r\nMember emails sent to:")
        logger.extend(bcc)
        email_text = MIMEText('\r\n'.join(logger))
        email_text['From'] = email_text['To'] = from_addr
        email_text['Subject'] = "Temple Recommend - Member emails"
        smtp.sendmail(from_addr, [from_addr], email_text.as_string())


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument('-e', action='store_true', help='send emails')
    parser.add_argument('--be', metavar='EMAIL', help='bishop email')
    parser.add_argument('--c1', metavar='EMAIL', help='first counselor email')
    parser.add_argument('--c2', metavar='EMAIL', help='second counselor email')
    parser.add_argument('--cfg', metavar='FILE', default='config.cfg',
                        help='configuration file')
    parser.add_argument('--test', action='store_true',
                        help='send email with bishops name to self')

    args = parser.parse_args()

    with lds_org.session() as lds:
        callings = lds.get('callings-with-dates').json()
        predicate = lambda x: x['position'] in BISHOPRIC.keys()
        people = map(PeopleAdapter, filter(predicate, callings))
        bishopric = dict((BISHOPRIC[_.position], _) for _ in people)

        if args.be:
            bishopric['bishop']._data['email'] = args.be
        if args.c1:
            bishopric['counselor1']._data['email'] = args.c1
        if args.c2:
            bishopric['counselor2']._data['email'] = args.c2

        recommends = lds.get('temple-recommend-status').json()
        rg = RecommendGroup(config_file=args.cfg)
        rg.select_recommends(recommends)
        if args.e or args.test:
            server = email_markdown.get_smtp(args.cfg, 'SMTP')
            rg.send_member_notices(server, bishopric, recommends,
                                   test=args.test)
            rg.send_email_to_bishopric(server, 'BISHOP', bishopric,
                                       test=args.test)
            rg.send_email_to_bishopric(server, 'COUNSELOR', bishopric,
                                       test=args.test)
        else:
            g = sorted(rg.groups.items(), key=lambda x: x[-1][-1])
            for v in g:
                title = v[-1][-1]
                print(title)
                print('=' * len(title))
                print(rg.report[v[0]])
