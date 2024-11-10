from typing import Literal

from .base import BaseAnthropicTool, ToolResult


class RecordTestResultTool(BaseAnthropicTool):
    """
    A tool that records the results of UI test cases by accepting a test ID and status.
    """

    api_type: Literal["custom"] = "custom"
    name: Literal["record_test_result"] = "record_test_result"
    description: str = "Record the result of a test case to database."
    input_schema: dict = {
        "type": "object",
        "properties": {
            "test_id": {"type": "string", "description": "The ID of the test case."},
            "status": {"type": "string", "description": "The status of the test case."},
        },
        "required": ["test_id", "status"],
    }

    def __init__(self):
        super().__init__()

    async def __call__(self, test_id: str, status: str, **kwargs) -> ToolResult:
        print(f"Recording result - Test ID: {test_id}, Status: {status}")
        return ToolResult(system="Result recorded successfully.")

    def to_params(self) -> dict:
        return {
            "type": self.api_type,
            "name": self.name,
            "description": self.description,
            "input_schema": self.input_schema,
        }

    