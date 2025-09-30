from sfa.database import client1


class location_tool:
    def __init__(self):
        self.main_database = client1['field_squad']
        # collection holding the provided location schema
        self.location_master = self.main_database['location_master']

    def unique(self, request_data: dict):
        # Normalize inputs
        state = (request_data or {}).get('statename') or (request_data or {}).get('state')
        district = (request_data or {}).get('district')

        # Case 1: No payload or no filters -> unique states
        if not state and not district:
            states = self.location_master.distinct('statename')
            states = [s for s in states if s not in (None, '')]
            states.sort()
            return {
                "level": "state",
                "data": states
            }

        # Case 2: State provided only -> unique districts in state
        if state and not district:
            query = {"statename": str(state)}
            districts = self.location_master.distinct('district', query)
            districts = [d for d in districts if d not in (None, '')]
            districts.sort()
            return {
                "level": "district",
                "statename": str(state),
                "data": districts
            }

        # Case 3: State and district provided -> unique office names in combo
        query = {"statename": str(state), "district": str(district)}
        offices = self.location_master.distinct('officename', query)
        offices = [o for o in offices if o not in (None, '')]
        offices.sort()
        return {
            "level": "office",
            "statename": str(state),
            "district": str(district),
            "data": offices
        }


