from sfa.services.web_followup_service import followup_tool


class followup_middleware:
    def __init__(self):
        self.followup_service = followup_tool()

    def followup_list(self, request_data: dict):
        return self.followup_service.followup_list(request_data)

    def followup_details(self, request_data: dict):
        return self.followup_service.followup_details(request_data)
