from config import settings
import json
import pandas as pd
import pytz
from bson import ObjectId
from sfa.database import client1
from datetime import datetime, timedelta
import re

class users_tool:
    def __init__(self):
        self.client_database = client1['talbros']
        self.all_type = self.client_database["all_type"]
        self.users = self.client_database["users"]
      
    def users_types(self, query: str):

        all_data = pd.DataFrame(list(self.all_type.find(query, {})))
        if all_data.empty:
            return []
        all_data_json = json.loads(
            all_data.to_json(orient="records", default_handler=str)
        )
        return all_data_json

    