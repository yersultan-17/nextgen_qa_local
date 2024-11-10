import dotenv

dotenv.load_dotenv("../.env")

from typing import Dict, List
from datetime import datetime
from tools.spreadsheet import get_test_case_data, update_cell, get_url

from atlassian import Jira
import os

jira = Jira(
    url='https://nextgen-qa.atlassian.net',
    username='bayram.annakov@gmail.com',
    token=os.getenv('JIRA_TOKEN'))


def create_issue(summary: str, description: str) -> Dict:
    """
    Create a Jira issue.
    
    Args:
        summary (str): Issue summary
        description (str): Issue description
        
    Returns:
        Dict: Created issue data
    """
    issue_fields = {
        "fields": {
            "project": {"key": "NQ"},
            "summary": summary,
            "description": description,
            "issuetype": {"name": "Bug"},
        }
    }

    try:
        response = jira.issue_create(fields=issue_fields)
        return {
            'key': response['key'],
            'self': response['self'],
        }
    except Exception as e:
        print(f"An error occurred: {e}")
        return None

def create_jira_issues_for_failures(spreadsheet_id: str, failed_rows: List[List]) -> List[Dict]:
    """
    Create Jira issues for failed test cases.
    
    Args:
        sheets_service: Google Sheets service instance
        spreadsheet_id (str): The ID of the spreadsheet
        failed_rows (List[List]): List of rows containing failed test case data
        
    Returns:
        List[Dict]: List of created Jira issues
    """
    created_issues = []
    test_cases = get_test_case_data(spreadsheet_id)
    
    headers = test_cases[0]
    id_col = headers.index('ID')
    title_col = headers.index('Title')
    desc_col = headers.index('Description')
    steps_col = headers.index('Steps')
    expected_col = headers.index('Expected Results')
    jira_col = headers.index('Jira Issue') if 'Jira Issue' in headers else len(headers)

    for row in failed_rows:
        if len(row) > jira_col and row[jira_col]:
            continue
            
        summary = f"Failed Test Case: {row[title_col]} ({row[id_col]})"
        description = f"""
Test Case Failed: {row[id_col]}

Description:
{row[desc_col]}

Steps to Reproduce:
{row[steps_col]}

Expected Results:
{row[expected_col]}

Test Environment:
- Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
- Spreadsheet: {get_url(spreadsheet_id)}
"""
        
        try:
            jira_response = create_issue(summary, description)
            if jira_response:
                created_issues.append({
                    'test_case_id': row[id_col],
                    'jira_key': jira_response['key'],
                    'summary': summary
                })
                
                # Update spreadsheet with Jira reference
                row_num = failed_rows.index(row) + 2
                jira_url = f"https://nextgen-qa.atlassian.net/jira/software/c/projects/NQ/issues/{jira_response['key']}"
                update_cell(
                    spreadsheet_id,
                    f'Test Cases!{chr(65 + jira_col)}{row_num}',
                    jira_url
                )
                
                print(f"Created Jira issue for test case {row[id_col]}")
                    
        except Exception as e:
            print(f"Error creating Jira issue for test case {row[id_col]}: {str(e)}")
            continue
            
    return created_issues

create_issue("Test", "Test")