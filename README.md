LDS Temple Recommend Expiring Notice
=====================================

There is a lot to keep up with: home, work, church, community.  Knowing
when your temple recommend is going to expire is something way in the
back of most peoples mind.  During one Bishopric meeting, the discussion
turned to recommend renewals.  The counselors can do most of the renewals,
helping to lighten the bishop's load.  However, if a counselor approaches
a member about a renewal, there is a possibility the member may feel
pressured to renew a recommend when they really need to speak with the
bishop.  I was asked to look into the possiblity of sending courtesy
email notices on expiring recommends.

This creates and sends emails to the current bishop, his counselors, and
members using the wards current callings and email addresses in LDS.org.
No need to twiddle with settings as people come and go in their callings.

Temple recommend information is on LDS.org, but this uses the
(LDS-org)[https://github.com/jidn/LDS-org] module to easily get data from
the *temple-recommend-status* endpoint.
The information is all on the LCR report.  I use the source of that report
to create any of the the following:

  * Bishop email with included reports.
  * Counselors email with included reports.
  * Member emails

Most clerks don't have the programming background that I do, so my goal is
to walk you through getting this to work for you.
I wanted to create something that can be used with limited knowledge
in Python, so I have a configuration file handling most of the options.

There are two ways to run this.  Either install the software on your computer or use the cloud.  I am going to recommend using the cloud for the following reasons.

  1. You don't need to use your personal computer with all the associated
     software maintance.
  2. You can have the cloud automatically schedule the emails.

Go to the Wiki and I'll walk you through setting up your own temple recommend
expiring reminder system.
