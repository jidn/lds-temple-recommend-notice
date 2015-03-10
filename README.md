LDS Temple Recommend Expiring Notice
=====================================

There is a lot to keep up with: home, work, church, community.  Knowing
when your temple recommend is going to expire is something way in the
back of most peoples mind.  During one Bishopric meeting, the discussion
turned to recommend renewals.  The counselors can do most of the renewals,
helping to lighten the bishop's load.  However, if a counselor approaches
a member about a renewal, there is apossibility the member may feel
pressured to renew a recommend when they really need to speak with the
bishop.  I was asked to look into the possiblity of sending courtesy
email notices on expiring recommends.

The information is all on the LCR report.  I use that report to create
any of the the following:

  * Bishop / Executive Secretary email with the content of that report.
    This does nothing but actively push this information to the bishop.
  * Counselors email on only the expiring recommends, which are the
    only ones they can renewal.
  * Undisclosed recipants to the individuals in the groups:
    - Expiring next month
    - Expiring this month
    - Expired less than one month
    - Expired over three months

I wanted to create something that can be used with limited knowledge
in Python, so I have a configuration file handling most of the options.
This is not a downloadable executable.  If interest is high enough, I
can do something to help you.  Leave a request at
[github](github.com/jidn/lds-temple-recommend-notice) or see the wiki
there.

Install
---------------------------------

First, you need to have python installed.  Refer to [python download](https://www.python.org/downloads/) and install a 2.7 release.  I have not tested
with a 3.X release.

Install LDS-org, lxml, and markdown.  [LDS-org](https://pypi.python.org/pypi/LDS-org) accesses the [LDS.org](www.lds.org) website using your username/password credentials, lxml parses the recommend information from LDS.org, and markdown formats your emails

    pip install LDS-org markdown lxml

Either download the tarball from [github](https://github.com/jidn/lds-temple-recomment-notice/archive/master.zip) or just clone the project.

    git clone https://github.com/jidn/lds-temple-recommend-notice.git

Copy the sample configuration file into the same directory with the README.md file and change the settings as described below.

Copy the sample template files into the same directory with the README.md and change them as needed with such information as how to secure an appointment with a member of the stake presidency.

Test your settings!!!  Make sure things are correct and then run it periodically to notify people about their upcoming or recently expired recommends.  There is very few things as annoying as getting to the temple only to realize the your commend has expired.

Configuration File
---------------------------------

There are four sections: LDS.org, SMTP, Email, and Testing.  In the
sample directory, you will find an example temple.cfg file.  Changing
the values there is a simple way to get you started.  Lets explain what
these values mean.

### LDS.org

We need to access LDS.org with your username and password, which do not
go through any third party.  We use the
[LDS-org](https://pypi.python.org/pypi/LDS-org) module.

    [LDS.org]
    username = your LDS.org username
    password = your LDS.org password


### SMTP

The simple mail transport protocal is all about sending emails.  Here
we put the information needed to send all of our different emails.

*USERNAME:* is the email username given to you by your email provider

*PASSWORD:* the password you use to send/receive email

*DOMAIN:* the domain name and optionally the port used to send email. For example google uses "smtp.gmail.com:587"

*TLS:* Do we use transport layer security? This should be yes for secure email and your email provider should use this.

    [SMTP]
    USERNAME = email username
    PASSWORD = email password
    DOMAIN = smtp.gmail.com:587
    TLS = true

### Testing

Before you send out emails, you may want to verify they work and look
correctly.  Here are some options that can help you.

*STDOUT_SERVER:* This is a fake smtp server.  It overrides all the
    options in the SMTP section. Instead of sending email, It just
    shows the email as if it was sending it out.  This isn't going
    to be readable, but you can check *To*, *From*, *Subject*, and
    any other email header.  It is a good test to verify emails are
    going to the people you think they are.

*TO_ADDR:* Send all emails to this email address or addresses, instead
    of their indended recipients.  This way you can check all the
    emails and notices.  If you specify more than one, seperate them
    with a comma and a space.

    [Testing]
    STDOUT_SERVER = false
    #TO_ADDR

### Email

*FROM_ADDR:* The name and address shown on the email as the source of
    the email. You can do this two different ways.  First, simply put
    just your email address.  Second you can put your name and email
    address between <> like `"my name <email@example.com>"`.  This way
    name could be a title like "Ward Reminder" or anything else you want.

*BCC_ADDR:* Send a copy of all emails to this person or persons.  Comment
    out this line if you don't wish to use it.

*BISHOP:*  Send an email to the bishop and executive secretary.  This
    contains the same information as found on the LDS report.

*COUNSELOR:* Send an email to the two bishop counselors containing the
    list of recommends that are about to expire.

*EXPIRING_NEXT_MONTH:* The template file used to send a email to those
    whos recommend will be expiring next month.

*EXPIRING_THIS_MONTH:* The template file used to send a email to those
    whos recommend will be expiring this month.

*EXPIRED_LESS_THAN_1_MONTH:* The template file used to send an email to
    those whos recommend has expired less than one month.

*EXPIRED_LAST_3_MONTHS:* The template file used to send an email to
    those whos recommend has expired within the last three months.

*EXPIRED_OVER_3_MONTHS:* The template file used to send an email to
    those whos recommend has expired over three months.  I don't
    expect many to use this, but it is here for completeness.

    [Email]
    BISHOP = true
    COUNSELOR = true
    EXPIRING_NEXT_MONTH = expiring-next-month.md
    EXPIRING_THIS_MONTH = expiring-this-month.md
    #EXPIRED_OVER_3_MONTHS =

Template
--------------------------------

Notices are not send to individuals, but as a group send, and no personal details are sent with it.  This is a text file in [Markdown](http://daringfireball.net/projects/markdown/syntax) format, so it will create an HTML email from a text file.  There are some ways to put bishopric information into the template.  Now as the bishopric changes the template can remain the same.  Here is a list of the available subsitituation.  Remember that they must be surrounded with braces {} to work correctly.    However, bishopric information is pulled from LDS.org so as people change in the bishopric, no changes need to be made to the template.  Here is the list of available items:

    {wardName}: The name of the ward as given by LDS.org
    {bishop}: Bishop
    {counselor1}: First counselor
    {counselor2}: Second counselor
    {exec_sec}: Executive secretary
    {wardclerk}: Ward clerk

By themself, this will show all their membership information from the LDS.org directory.You will want to use it with one of the following, remember it can be any of the above 5 people:

    {bishop[surname]}: surname or last name
    {bishop[email]}: personal email address
    {bishop[phone]}: personal phone number
    {bishop[preferredName]}: perferred name

