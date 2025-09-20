from trust_rewards.services.web_customer_service import customer_tool


class CustomerDataProcessor:
    def customer_add(self, request_data):
        processor = customer_tool()
        if request_data.get('_id') or request_data.get('id'):
            return processor.update_customer(request_data)
        return processor.add_customer(request_data)

    def customers_list(self, request_data):
        processor = customer_tool()
        return processor.customers_list(request_data)

    def customer_details(self, request_data):
        processor = customer_tool()
        return processor.customer_details(request_data)

    def customer_image_update(self, customer_id, upload_file):
        processor = customer_tool()
        return processor.update_customer_image(customer_id, upload_file)


