from sfa.services.web_beat_plan_service import beat_plan_tool


class beat_plan_middleware:
    def __init__(self):
        self.beat_plan_service = beat_plan_tool()

    def beat_plan_list(self, request_data: dict):
        return self.beat_plan_service.beat_plan_list(request_data)

    def beat_plan_details(self, request_data: dict):
        return self.beat_plan_service.beat_plan_details(request_data)
