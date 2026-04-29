from pydantic import BaseModel


class ChatRequest(BaseModel):
    message: str


class ChatResponse(BaseModel):
    state: dict
    tools_used: list
    tool_results: dict