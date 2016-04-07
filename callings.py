"""
Calling:
    callingName: calling
    groupname: organization or group
    individualId (int): personal identifying number
    groupInstance (int): number
    groupKey (int): number
    positionId (int): number

Calling-v2:
    list of dicts with the following:
        displayOrder (int):
        instanceId (int):
        name (str): Organization name
        orgTypeId (int):
        assignmentsInGroup (list): of dicts with following:
            dateActivated: long integer, epoch?
            dateSetApart: long integer, epoch?
            displayOrder (int):
            individualId (int):
            positionName (str): calling title
            positionTypeId (int):
            setApartFlg (bool):

Household:
    This is a list of households.  Every household has a single head
    of house.  Other people include 'spouse', and 'children'.

    param dict headOfHouse:
        surname: 'Surname'
        formattedName: 'Surname, First'
        directoryName: 'Surname, First'
        givenName1: 'First Middle'
        preferredName: 'Last, Prefered'
        photoUrl: URL
        individualId: unique number
        memberId: membership number
        birthdate:
        email: personal email
        phone: personal phone number
    spouse (dict): see headOfHouse
    children (list): list similar to headOfHouse
    coupleName (str): 'Surname, First & First' or formattedName
    emailAddress (str): household email
    phone (str): household number
    householdName (str): Surname
    familyPhotoUrl (str): URL
    hidHouseholdPhoto (bool):
    headOfHouseIndividualId (str): sames as headOfHouse['individualId']
    latitude:
    longitude:
    optOut:

    # Address information
    desc1: address line 1
    desc2: address line 2
    desc3: address line 3
    desc4: address line 4
    desc5: address line 5
    city: address city
    state: address state
    postalCode: address postal code

Household-v2
    List of dicts with the following

    coupleName (str): Last, Husband & Wife
    emailAddress (str?): Household email adress
    phone (str?): formatted phone number
    headOfHouse (dict):
        email (str?): individual email
        phone (str?): individual formatted phone number
        fullName (str): Last, first middle
        givenName (str): first middle
        preferredName (str): Last, first
        surname (str): Last
        individualId (int):
        memberID (str): membership number with dashes
    spouse (dict?): Same as headOfHouse
    children (list?): List of dict same as headOfHouse
    headOfHouseIndividualId (int):
    householdName (str): Last
    includeLatLong (bool):
    latitude (float):
    longitude (float):
    desc1 (str): first line of address
    desc2 (str): second line of address
    descN (str): formatted "City, State ZIP'
    state (str): long state name
    postalCode (str): zipcode
"""


class Membership(object):
    """
    Information from LDS.org is in three groups:
        'households':
        'callings'
        'unitNo'
    """
    def __init__(self, data):
        self._callings = data['callings']
        self._households = data['households']
        self._unitNo = data['unitNo']
        self._make_membership()

    def __getitem__(self, item):
        "Search membership by individualId or durname"
        return self.membership[item]

    def organization(self, lens=None):
        """
        """
        return [_ for _ in self._callings if lens(_)]

    def bishopric(self):
        """Returns a dict of bishopric excluding any assistant clerks.
        Keys are: bishop, counselor1, counselor2, wardclerk, exec_sec
        Values are the same as any member, but also adds 'callingName'
        """
        lens = lambda x: x['groupName'] == 'Bishopric' and 'Assistant' not in x['callingName']
        data = {}
        titles = {'Bishop': 'bishop',
                  'Bishopric First Counselor': 'counselor1',
                  'Bishopric Second Counselor': 'counselor2',
                  'Ward Executive Secretary': 'exec_sec',
                  'Ward Clerk': 'wardclerk'}
        for call in self.organization(lens):
            data[titles[call['callingName']]] = self.membership[int(call['individualId'])]
        return data

    def _make_membership(self):
        self.membership = {}

        for household in self._households:
            address = {}
            house = {'address': address}
            def add(person):
                person['house'] = house
                self.membership[int(person['individualId'])] = person
                self.membership.setdefault(person['surname'], []).append(person)

            for k, v in household.items():
                if k in ('city', 'state', 'postalCode') or k[:4] == 'desc':
                    address[k] = v
                elif k not in ('headOfHouse', 'spouse', 'children'):
                    house[k] = v

            head = household.pop('headOfHouse')
            add(head)
            spouse = household.pop('spouse')
            children = household.pop('children')
            if spouse:
                head['spouse'] = spouse
                spouse['spouse'] = head
                add(spouse)
            for child in children:
                child['house'] = house
                child['parent'] = house
                add(child)
            head['children'] = children
            if spouse:
                spouse['children'] = children

