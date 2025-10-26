from trust_rewards.services.web_location_service import location_tool


class LocationDataProcessor:
    def unique(self, request_data):
        processor = location_tool()
        return processor.unique(request_data)


