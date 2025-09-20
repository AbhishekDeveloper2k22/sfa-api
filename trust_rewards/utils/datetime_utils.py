import pytz
from datetime import datetime


class important_utilities:
    def __init__(self):
        pass

    ## Function for Current Time & Date as per timezone
    def current_time_and_date(self):
        try:
            # Define the user's timezone
            user_tz = pytz.timezone("Asia/Kolkata")

            # Get the current UTC time
            current_utc_time = datetime.now(tz=pytz.UTC)

            # Convert the current UTC time to the user's timezone
            current_datetime_in_tz = current_utc_time.astimezone(user_tz)

            # Format the current date and time in the specified format
            formatted_datetime = current_datetime_in_tz.strftime("%d-%m-%Y %I:%M %p")
            download_time_format = current_datetime_in_tz.strftime("%Y%m%d_%H%M%S")

            return formatted_datetime, download_time_format
        except Exception:
            return "00-00-0000 00:00 AM", "00000000_000000"

