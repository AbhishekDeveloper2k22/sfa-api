from trust_rewards.database import client1


class location_tool:
    def __init__(self):
        self.main_database = client1['trust_rewards']
        # collection holding the provided location schema
        self.location_master = self.main_database['location_master']

    def unique(self, request_data: dict):
        # Normalize inputs
        state = (request_data or {}).get('statename') or (request_data or {}).get('state')
        district = (request_data or {}).get('district')
        pincode = (request_data or {}).get('pincode')

        # Case 0: Only pincode provided -> return full location array
        if pincode and not state and not district:
            locations = list(self.location_master.find({"pincode": str(pincode)}))
            if locations:
                # Convert to array of location objects
                location_objects = []
                for location in locations:
                    location_objects.append({
                        "statename": location.get('statename'),
                        "district": location.get('district'),
                        "officename": location.get('officename'),
                        "pincode": location.get('pincode'),
                        "latitude": location.get('latitude'),
                        "longitude": location.get('longitude'),
                        "officetype": location.get('officetype'),
                        "delivery": location.get('delivery')
                    })
                return {
                    "level": "full_location",
                    "data": location_objects
                }
            else:
                return {
                    "level": "full_location",
                    "data": [],
                    "message": "Pincode not found"
                }

        # Case 1: No payload or no filters -> unique states
        if not state and not district:
            states = self.location_master.distinct('statename')
            states = [s for s in states if s not in (None, '')]
            states.sort()
            # Convert to objects with statename key
            state_objects = [{"statename": s} for s in states]
            return {
                "level": "state",
                "data": state_objects
            }

        # Case 2: State provided only -> unique districts in state
        if state and not district:
            query = {"statename": str(state)}
            districts = self.location_master.distinct('district', query)
            districts = [d for d in districts if d not in (None, '')]
            districts.sort()
            # Convert to objects with district key
            district_objects = [{"district": d} for d in districts]
            return {
                "level": "district",
                "statename": str(state),
                "data": district_objects
            }

        # Case 3: State and district provided -> unique office names in combo
        query = {"statename": str(state), "district": str(district)}
        offices = self.location_master.distinct('officename', query)
        offices = [o for o in offices if o not in (None, '')]
        offices.sort()
        
        # Build office -> pincodes mapping objects
        office_pincode_data = []
        for office in offices:
            office_query = {"statename": str(state), "district": str(district), "officename": office}
            office_pincodes = self.location_master.distinct('pincode', office_query)
            office_pincodes = [p for p in office_pincodes if p not in (None, '')]
            office_pincodes.sort()
            
            # If only one pincode, return as single value, otherwise as array
            pincode_value = office_pincodes[0] if len(office_pincodes) == 1 else office_pincodes
            
            office_pincode_data.append({
                "officename": office,
                "pincodes": pincode_value
            })
        
        return {
            "level": "office",
            "statename": str(state),
            "district": str(district),
            "data": office_pincode_data
        }


