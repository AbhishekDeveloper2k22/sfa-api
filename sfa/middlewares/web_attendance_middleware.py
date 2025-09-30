from sfa.services.web_attendance_service import attendance_tool


class AttendanceDataProcessor:
    def attendance_list(self, request_data):
        processor = attendance_tool()
        return processor.attendance_list(request_data)


