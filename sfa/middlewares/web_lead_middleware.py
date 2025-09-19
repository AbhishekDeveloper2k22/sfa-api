from sfa.services.web_lead_service import lead_tool


class LeadDataProcessor:
    def lead_add(self, request_data):
        processor = lead_tool()
        if request_data.get('_id') or request_data.get('id'):
            return processor.update_lead(request_data)
        return processor.add_lead(request_data)

    def lead_details(self, request_data):
        processor = lead_tool()
        return processor.lead_details(request_data)

    def leads_list(self, request_data):
        processor = lead_tool()
        return processor.leads_list(request_data)

    def lead_image_update(self, lead_id, upload_file):
        processor = lead_tool()
        return processor.update_lead_image(lead_id, upload_file)


