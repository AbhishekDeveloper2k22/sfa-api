from pydantic import BaseModel, Field
from typing import Optional, Dict, Any

class GenerateRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=1000, description="User's natural language query")

class GenerateResponse(BaseModel):
    success: bool = Field(..., description="Whether the request was successful")
    msg: str = Field(..., description="Response message")
    statuscode: int = Field(..., description="HTTP status code")
    data: Optional[Dict[str, Any]] = Field(None, description="Response data")

class ToolCallRequest(BaseModel):
    tool_name: str = Field(..., description="Name of the tool to call")
    parameters: Optional[Dict[str, Any]] = Field(None, description="Optional parameters for the tool")

class ToolCallResponse(BaseModel):
    success: bool = Field(..., description="Whether the tool call was successful")
    msg: str = Field(..., description="Response message")
    statuscode: int = Field(..., description="HTTP status code")
    data: Optional[Dict[str, Any]] = Field(None, description="Tool execution result")

class HealthResponse(BaseModel):
    status: str = Field(..., description="Service status")
    timestamp: str = Field(..., description="Current timestamp")
    service: str = Field(..., description="Service name")

class ToolInfo(BaseModel):
    name: str = Field(..., description="Tool name")
    description: str = Field(..., description="Tool description")
    category: str = Field(..., description="Tool category")

class ToolsResponse(BaseModel):
    success: bool = Field(..., description="Whether the request was successful")
    msg: str = Field(..., description="Response message")
    statuscode: int = Field(..., description="HTTP status code")
    data: Dict[str, list] = Field(..., description="Available tools")
