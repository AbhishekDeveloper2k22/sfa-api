import os
import json
import requests
from datetime import datetime
from typing import Dict, List
from dotenv import load_dotenv
from bson import ObjectId
from trust_rewards.database import client1
from config import settings
from trust_rewards.services.database_schemas import SCHEMA_INFO

load_dotenv()

class WebTrustRewardsAIAgentService:
    def __init__(self):
        # Provider selection (only Hugging Face now)
        self.provider = "hf"
        print("MODEL_PROVIDER =", self.provider)

        # Hugging Face config
        self.hf_api_key = os.getenv("HUGGINGFACE_API_KEY")
        self.hf_model = os.getenv("HUGGINGFACE_MODEL", "HuggingFaceH4/zephyr-7b-beta")

        if not self.hf_api_key:
            raise ValueError("HUGGINGFACE_API_KEY is required for Hugging Face provider.")

        # MongoDB connection
        self.db = client1[settings.DB1_NAME]
        self.schema_info = SCHEMA_INFO

        # System Instruction (same as before)
        self.system_instruction = f"""
        You are an advanced AI Agent for Trust Rewards with DYNAMIC MongoDB query capabilities.
        
        🚨 ABSOLUTE RULES - FOLLOW THESE OR FAIL:
        1. YOU MUST CALL A TOOL FOR EVERY DATA REQUEST
        2. NEVER EVER create example data like "Category 1", "Category 2", "Description 1"
        3. If tool returns 0 results, say "No data found" - DO NOT create fake data
        4. If tool returns 1 result, show EXACTLY 1 result - NOT 2 or 3
        5. Copy EXACT field values from tool response - do not modify them
        6. The "data" field in your JSON response MUST be the EXACT tool result
        7. Tool result has 1 document? Show 1 document. Tool has 5? Show 5. Tool has 0? Show 0.
        
        🛑 STRICTLY FORBIDDEN:
        - Creating fake data when tool returns empty
        - Adding extra documents that tool didn't return
        - Modifying field values from tool response
        - Responding without calling any tool
        - Creating "example" or "sample" data
        
        📚 DATABASE SCHEMA:
        {json.dumps(self.schema_info, indent=2)}
        
        🔧 AVAILABLE OPERATIONS:
        - Query analysis: analyze_and_generate_query(user_request)
        - Execute generated: execute_generated_query(generated_query)
        - Simple queries: execute_query(collection, query, sort, limit)
        - Complex aggregation: execute_aggregation(collection, pipeline)
        - Count documents: execute_count(collection, query)
        - Distinct values: execute_distinct(collection, field, query)
        
        📊 RESPONSE FORMAT:
        Always return JSON with:
        {{
          "summary": "Brief answer to user's question",
          "details": {{"key": "value"}},
          "data": {{...}},
          "message": "Helpful insights"
        }}
        """

    # ------------------ HELPERS ------------------

    def _serialize_doc(self, doc: Dict) -> Dict:
        if doc is None:
            return None
        serialized = {}
        for key, value in doc.items():
            if isinstance(value, ObjectId):
                serialized[key] = str(value)
            elif isinstance(value, datetime):
                serialized[key] = value.isoformat()
            elif isinstance(value, dict):
                serialized[key] = self._serialize_doc(value)
            elif isinstance(value, list):
                serialized[key] = [self._serialize_doc(item) if isinstance(item, dict) else item for item in value]
            else:
                serialized[key] = value
        return serialized

    # ------------------ HUGGING FACE API CALL ------------------

    def _call_huggingface(self, prompt: str, max_tokens: int = 512) -> str:
        """Call Hugging Face Inference API."""
        url = f"https://api-inference.huggingface.co/models/{self.hf_model}"
        headers = {
            "Authorization": f"Bearer {self.hf_api_key}",
            "Accept": "application/json",
            "Content-Type": "application/json",
        }
        payload = {
            "inputs": prompt,
            "parameters": {"max_new_tokens": max_tokens, "return_full_text": False},
            "options": {"use_cache": True, "wait_for_model": True}
        }
        resp = requests.post(url, headers=headers, json=payload, timeout=120)
        resp.raise_for_status()
        data = resp.json()

        # Extract text
        if isinstance(data, list) and len(data) > 0:
            if isinstance(data[0], dict) and "generated_text" in data[0]:
                return data[0]["generated_text"]
            return str(data[0])
        if isinstance(data, dict) and "generated_text" in data:
            return data["generated_text"]
        return json.dumps(data)

    # ------------------ MODEL WRAPPER ------------------

    def _call_model(self, prompt: str) -> str:
        """Unified entry (only Hugging Face)."""
        return self._call_huggingface(prompt)

    # ------------------ QUERY ANALYSIS ------------------

    def analyze_and_generate_query(self, user_request: str) -> dict:
        prompt = f"{self.system_instruction}\n\nUser request: {user_request}\n\nReturn JSON with collection, query, sort, limit, pipeline (if aggregation). ONLY return valid JSON."
        try:
            model_resp = self._call_model(prompt)
            try:
                parsed = json.loads(model_resp)
                return {
                    "success": True,
                    "user_request": user_request,
                    "generated_query": parsed,
                    "explanation": "Query generated by model - not executed"
                }
            except Exception:
                return {
                    "success": True,
                    "user_request": user_request,
                    "generated_query_text": model_resp,
                    "note": "Model output not strict JSON. Needs manual parsing."
                }
        except Exception as e:
            return {"success": False, "error": str(e)}

    # ------------------ QUERY EXECUTION TOOLS ------------------

    def execute_query(self, collection_name: str, query: dict = None, sort: dict = None, limit: int = None, skip: int = None, projection: dict = None) -> dict:
        try:
            if collection_name not in self.schema_info:
                return {"success": False, "error": f"Collection '{collection_name}' not found. Available: {list(self.schema_info.keys())}"}
            collection = self.db[collection_name]
            query = query or {}
            cursor = collection.find(query, projection)
            if sort:
                cursor = cursor.sort(list(sort.items()))
            if skip:
                cursor = cursor.skip(skip)
            if limit:
                cursor = cursor.limit(limit)
            results = list(cursor)
            serialized_results = [self._serialize_doc(doc) for doc in results]
            return {"success": True, "count": len(serialized_results), "documents": serialized_results}
        except Exception as e:
            return {"success": False, "error": f"Query execution error: {str(e)}"}

    def execute_aggregation(self, collection_name: str, pipeline: List[dict]) -> dict:
        try:
            if collection_name not in self.schema_info:
                return {"success": False, "error": f"Collection '{collection_name}' not found"}
            collection = self.db[collection_name]
            results = list(collection.aggregate(pipeline))
            serialized_results = [self._serialize_doc(doc) for doc in results]
            return {"success": True, "count": len(serialized_results), "results": serialized_results}
        except Exception as e:
            return {"success": False, "error": f"Aggregation error: {str(e)}"}

    def execute_count(self, collection_name: str, query: dict = None) -> dict:
        try:
            if collection_name not in self.schema_info:
                return {"success": False, "error": f"Collection '{collection_name}' not found"}
            collection = self.db[collection_name]
            query = query or {}
            count = collection.count_documents(query)
            return {"success": True, "count": count}
        except Exception as e:
            return {"success": False, "error": f"Count error: {str(e)}"}

    def execute_distinct(self, collection_name: str, field: str, query: dict = None) -> dict:
        try:
            if collection_name not in self.schema_info:
                return {"success": False, "error": f"Collection '{collection_name}' not found"}
            collection = self.db[collection_name]
            query = query or {}
            distinct_values = collection.distinct(field, query)
            return {"success": True, "count": len(distinct_values), "values": distinct_values}
        except Exception as e:
            return {"success": False, "error": f"Distinct error: {str(e)}"}

    # ------------------ AI RESPONSE ------------------

    def generate_ai_response(self, user_message: str) -> dict:
        try:
            prompt = f"{self.system_instruction}\n\nUser Request:\n{user_message}\n\nRespond only in JSON with keys like: summary, details, generated_query, explanation."
            model_text = self._call_model(prompt)
            try:
                parsed = json.loads(model_text)
                return {"success": True, "json": parsed}
            except Exception:
                return {"success": True, "text": model_text, "note": "Model output not strict JSON."}
        except Exception as e:
            return {"success": False, "error": str(e)}
