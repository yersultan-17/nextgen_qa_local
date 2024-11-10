from typing import Dict, List
from datetime import datetime
from tools.jira import create_jira_issues_for_failures
from tools.spreadsheet import (
    get_test_case_data, update_cell, update_cell_color,
    get_sheet_ids, get_url
)

# Status colors dictionary
STATUS_COLORS = {
    'Passed': {'red': 0.7, 'green': 0.9, 'blue': 0.7},    # Light green
    'Failed': {'red': 0.9, 'green': 0.7, 'blue': 0.7},    # Light red
    'Blocked': {'red': 0.9, 'green': 0.85, 'blue': 0.7},  # Light orange
    'In Progress': {'red': 0.7, 'green': 0.7, 'blue': 0.9},  # Light blue
    'Skipped': {'red': 0.8, 'green': 0.8, 'blue': 0.8},   # Light gray
    'Not Started': {'red': 1, 'green': 1, 'blue': 1}      # White
}

VALID_STATUSES = {'Not Started', 'In Progress', 'Blocked', 'Failed', 'Passed', 'Skipped'}

def update_status(spreadsheet_id: str, test_case_id: str, status: str) -> str:
    """
    Update the status of a single test case.
    
    Args:
        spreadsheet_id (str): The ID of the spreadsheet
        test_case_id (str): The ID of the test case to update
        status (str): New status value
        
    Returns:
        str: Update result message
    """
    try:
        # Validate status
        if status not in VALID_STATUSES:
            raise ValueError(f"Invalid status value: {status}. Valid statuses are: {VALID_STATUSES}")

        # Get test cases data
        values = get_test_case_data(spreadsheet_id)
        if not values:
            raise ValueError("No test cases found in spreadsheet")
            
        # Find test case row and update
        headers = values[0]
        id_col = headers.index('ID')
        status_col = headers.index('Status')
        
        row_number = None
        row_data = None
        for idx, row in enumerate(values[1:], start=2):
            if row[id_col] == test_case_id:
                row_number = idx
                row_data = row
                break
                
        if not row_number:
            raise ValueError(f"Test case ID not found: {test_case_id}")
            
        # Update the status
        update_range = f'Test Cases!{chr(65 + status_col)}{row_number}'
        update_cell(spreadsheet_id, update_range, status)
        
        # Update color formatting
        sheet_ids = get_sheet_ids(spreadsheet_id)
        update_cell_color(
            spreadsheet_id,
            sheet_ids['Test Cases'],
            row_number,
            status_col,
            STATUS_COLORS[status]
        )
        
        # Create Jira issue if failed
        if status == 'Failed':
            print("Creating Jira issue for failed test case...")
            created_issues = create_jira_issues_for_failures(spreadsheet_id, [row_data])
            if created_issues:
                print(f"Created Jira issue: {created_issues[0]['jira_key']} - {created_issues[0]['summary']}")
        
        return f"Updated test case {test_case_id} status to {status}"
            
    except Exception as e:
        raise Exception(f"Error updating test case: {str(e)}")

def update_statuses(spreadsheet_id: str, updates: List[Dict[str, str]]) -> str:
    """
    Update the status of multiple test cases in batch.
    
    Args:
        sheets_service: Google Sheets service instance
        spreadsheet_id (str): The ID of the spreadsheet
        updates (List[Dict[str, str]]): List of updates, each containing 'id' and 'status'
        
    Returns:
        str: Update result message
    """
    try:
        results = []
        failed_updates = []
        
        for update in updates:
            try:
                result = update_status(
                    spreadsheet_id,
                    update['id'],
                    update['status']
                )
                results.append(result)
            except Exception as e:
                failed_updates.append({
                    'id': update['id'],
                    'error': str(e)
                })
        
        # Prepare result message
        success_count = len(results)
        fail_count = len(failed_updates)
        
        message = f"Updated {success_count} test case(s)"
        if fail_count > 0:
            message += f"\nFailed to update {fail_count} test case(s):"
            for fail in failed_updates:
                message += f"\n- {fail['id']}: {fail['error']}"
                
        return message
        
    except Exception as e:
        raise Exception(f"Error in batch update: {str(e)}")