"""
Calling:
    param callingName: calling
    param groupname: organization or group
    param individualId: personal identifying number
    param groupInstance: number
    param groupKey: number
    param positionId: number

Household:
    This is a list of households.  Every household has a single head
    of house.  Other people include 'spouse', and 'children'.

    param dict headOfHouse:
        param surname: 'Surname'
        param formattedName: 'Surname, First'
        param directoryName: 'Surname, First'
        param givenName1: 'First Middle'
        param preferredName: 'Last, Prefered'
        param photoUrl: URL
        param individualId: unique number
        param memberId: membership number
        param birthdate:
        param email: personal email
        param phone: personal phone number
    param dict spouse: see headOfHouse
    param list children: list similar to headOfHouse
    param str  coupleName: 'Surname, First & First' or formattedName
    param str  emailAddress: household email
    param str  phone: household number
    param str  householdName: Surname
    param URL  familyPhotoUrl: URL
    param bool hidHouseholdPhoto:
    param str  headOfHouseIndividualId: sames as headOfHouse['individualId']
    param latitude:
    param longitude:
    param optOut:

    # Address information
    param desc1: address line 1
    param desc2: address line 2
    param desc3: address line 3
    param desc4: address line 4
    param desc5: address line 5
    param city: address city
    param state: address state
    param postalCode: address postal code

"""
import lds_org


class Membership(object):
    """
    Information from LDS.org is in three groups:
        'households':
        'callings'
        'unitNo'
    """

    def __getitem__(self, item):
        "Search membership by individualId or durname"
        return self.membership[item]

    def organization(self, lens=None):
        """
        """
        return [_ for _ in self._callings if lens(_)]

    def get(self, lds=None):
        endpoint = 'unit-members-and-callings'
        if lds:
            rv = lds.get(endpoint)
            assert rv.status_code == 200
            self.data = rv.json()
        else:
            with lds_org.session as lds:
                rv = lds.get('unit-members-and-callings')
                assert rv.status_code == 200
                self.data = rv.json()

        self._callings = self.data['callings']
        self._households = self.data['households']
        self._unitNo = self.data['unitNo']

        self._make_membership()
        return self

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

