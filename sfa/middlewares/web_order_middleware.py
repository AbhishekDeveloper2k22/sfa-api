from sfa.services.web_order_service import order_tool


class order_middleware:
    def __init__(self):
        self.service = order_tool()

    def order_list(self, request_data: dict):
        return self.service.order_list(request_data)

    def order_details(self, request_data: dict):
        return self.service.order_details(request_data)

    def order_update(self, request_data: dict):
        return self.service.order_update(request_data)


