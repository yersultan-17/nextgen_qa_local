import dotenv

dotenv.load_dotenv("../.env")

from typing import Dict, List, Optional
from datetime import datetime
from tools.spreadsheet import get_test_case_data, update_cell, get_url

from atlassian import Jira
import os

jira = Jira(
    url='https://nextgen-qa.atlassian.net',
    username='bayram.annakov@gmail.com',
    password=os.getenv('JIRA_TOKEN'),
    cloud=True)

def attach_base64_image(issue_key: str, base64_image: str, filename: str = "screenshot.png") -> bool:
    """
    Attach a base64 encoded image to a Jira issue.
    
    Args:
        issue_key (str): The Jira issue key
        base64_image (str): Base64 encoded image string
        filename (str): Name for the attached file
        
    Returns:
        bool: True if attachment was successful, False otherwise
    """
    try:
        # Remove data URL prefix if present
        if ',' in base64_image:
            base64_image = base64_image.split(',')[1]
        
        # Decode base64 string to bytes
        image_data = base64.b64decode(base64_image)
        
        # Create file-like object
        file_obj = io.BytesIO(image_data)
        
        # Attach to Jira issue
        jira.add_attachment(
            issue_id=issue_key,
            filename=filename,
            attachment=file_obj
        )
        print(f"Successfully attached image to {issue_key}")
        return True
        
    except Exception as e:
        print(f"Error attaching image to {issue_key}: {e}")
        return False


def create_issue(summary: str, description: str, base64_image: Optional[str] = None) -> Dict:
    """
    Create a Jira issue with optional screenshot attachment.
    
    Args:
        summary (str): Issue summary
        description (str): Issue description
        screenshot_path (str, optional): Path to screenshot file
        
    Returns:
        Dict: Created issue data
    """
    issue_fields = {
        "project": {"key": "NQ"},
        "summary": summary,
        "description": description,
        "issuetype": {"name": "Bug"},
    }
    
    try:
        # Create the issue
        response = jira.issue_create(fields=issue_fields)
        print(f"Created issue: {response['key']}")
        
        # Attach screenshot if provided
        if base64_image:
            attach_base64_image(response['key'], base64_image)
            print(f"Attached screenshot to {response['key']}")
        
        return {
            'key': response['key'],
            'self': response['self'],
        }
    except Exception as e:
        print(f"An error occurred: {e}")
        return None

def create_jira_issues_for_failures( 
    spreadsheet_id: str, 
    failed_rows: List[List],
    screenshots_dict: Optional[Dict[str, str]] = None
) -> List[Dict]:
    """
    Create Jira issues for failed test cases.
    
    Args:
        spreadsheet_id (str): The ID of the spreadsheet
        failed_rows (List[List]): List of rows containing failed test case data
        screenshots_dict (Dict[str, str], optional): Dictionary mapping test case IDs to screenshot paths
        
    Returns:
        List[Dict]: List of created Jira issues
    """
    created_issues = []
    test_cases = get_test_case_data(spreadsheet_id)
    headers = test_cases[0]
    
    # Get column indices
    column_indices = {
        'id': headers.index('ID'),
        'title': headers.index('Title'),
        'desc': headers.index('Description'),
        'steps': headers.index('Steps'),
        'expected': headers.index('Expected Results'),
        'jira': headers.index('Jira Issue') if 'Jira Issue' in headers else len(headers)
    }
    
    for row in failed_rows:
        # Skip if Jira issue already exists
        if len(row) > column_indices['jira'] and row[column_indices['jira']]:
            continue
            
        test_case_id = row[column_indices['id']]
        summary = f"Failed Test Case: {row[column_indices['title']]} ({test_case_id})"
        description = f"""
Test Case Failed: {test_case_id}
Description:
{row[column_indices['desc']]}

Steps to Reproduce:
{row[column_indices['steps']]}

Expected Results:
{row[column_indices['expected']]}

Test Environment:
- Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
- Spreadsheet: {get_url(spreadsheet_id)}
"""
        try:
            # Get screenshot path for this test case if available
            base64_image = screenshots_dict.get(test_case_id) if screenshots_dict else None
                
                # Create issue with screenshot if available
                jira_response = create_issue(summary, description, base64_image)
            
            if jira_response:
                created_issues.append({
                    'test_case_id': test_case_id,
                    'jira_key': jira_response['key'],
                    'summary': summary
                })
                
                # Update spreadsheet with Jira reference
                row_num = failed_rows.index(row) + 2
                jira_url = f"https://nextgen-qa.atlassian.net/browse/{jira_response['key']}"
                update_cell(
                    spreadsheet_id,
                    f'Test Cases!{chr(65 + column_indices["jira"])}{row_num}',
                    jira_url
                )
                print(f"Created Jira issue for test case {test_case_id}")
                
        except Exception as e:
            print(f"Error creating Jira issue for test case {test_case_id}: {str(e)}")
            continue
            
    return created_issues


#print(jira.get_issue("NQ-1"))
#create_issue("Test", "Test", "screenshot.jpg")