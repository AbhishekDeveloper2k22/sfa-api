from trust_rewards.services.web_product_service import product_tool


class ProductDataProcessor:
    def product_add(self, request_data):
        processor = product_tool()
        if request_data.get('_id') or request_data.get('id'):
            return processor.update_product(request_data)
        return processor.add_product(request_data)

    def products_list(self, request_data):
        processor = product_tool()
        return processor.products_list(request_data)

    def product_details(self, request_data):
        processor = product_tool()
        return processor.product_details(request_data)

    def product_image_update(self, product_id, upload_file):
        processor = product_tool()
        return processor.update_product_image(product_id, upload_file)


