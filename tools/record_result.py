import base64

from typing import Literal
from pathlib import Path

from .base import BaseAnthropicTool, ToolResult
from tools.test_case_manager import update_status, VALID_STATUSES

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
            "spreadsheet_id": {"type": "string", "description": "The ID of the spreadsheet."},
            "test_id": {"type": "string", "description": "The ID of the test case."},
            "status": {"type": "string", "enum": list(VALID_STATUSES), "description": "The status of the test case."},
        },
        "required": ["spreadsheet_id", "test_id", "status"],
    }

    def __init__(self):
        super().__init__()

    async def __call__(self, spreadsheet_id: str, test_id: str, status: str, **kwargs) -> ToolResult:
        print(f"Recording result - Test ID: {test_id}, Status: {status}")
        screenshot = sorted(Path("/tmp/outputs").glob("screenshot_*.png"), key=lambda p: p.stat().st_mtime)[-1]
        print(f"Screenshot path: {screenshot}")
        screenshot_base64 = base64.b64encode(screenshot.read_bytes()).decode()
        update_status(spreadsheet_id, test_id, status, screenshot_base64)
        return ToolResult(system="Result recorded successfully.")

    def to_params(self) -> dict:
        return {
            "type": self.api_type,
            "name": self.name,
            "description": self.description,
            "input_schema": self.input_schema,
        }

    