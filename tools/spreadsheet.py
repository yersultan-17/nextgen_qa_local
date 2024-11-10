from typing import Dict, List, Tuple
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

GOOGLE_CREDS_FILE = "empatika-labs-sales-20e446c8764d.json"



def get_spreadsheet_services(google_creds_file: str):
    """Initialize Google Sheets and Drive services."""
    creds = service_account.Credentials.from_service_account_file(
        google_creds_file,
        scopes=[
            'https://www.googleapis.com/auth/spreadsheets',
            'https://www.googleapis.com/auth/drive'
        ]
    )
    sheets_service = build('sheets', 'v4', credentials=creds)
    drive_service = build('drive', 'v3', credentials=creds)
    return sheets_service, drive_service

def verify_access(spreadsheet_id: str) -> bool:
    """Verify if the service account has access to the spreadsheet."""
    try:
        sheets_service.spreadsheets().get(
            spreadsheetId=spreadsheet_id,
            fields='spreadsheetId'
        ).execute()
        return True
    except HttpError as error:
        if error.resp.status == 403:
            return False
        raise error

def ensure_editor_access( spreadsheet_id: str, email: str):
    """Ensure the service account has editor access to the spreadsheet."""
    try:
        permissions = drive_service.permissions().list(
            fileId=spreadsheet_id,
            fields='permissions(id,emailAddress,role)'
        ).execute()

        for permission in permissions.get('permissions', []):
            if permission.get('emailAddress') == email and permission.get('role') == 'writer':
                return

        permission = {
            'type': 'user',
            'role': 'writer',
            'emailAddress': email
        }
        
        drive_service.permissions().create(
            fileId=spreadsheet_id,
            body=permission,
            fields='id',
            sendNotificationEmail=False
        ).execute()

    except HttpError as error:
        raise Exception(f"Error ensuring editor access: {str(error)}")

def create_spreadsheet(title: str) -> Tuple[str, Dict[str, int]]:
    """Create a new Google Spreadsheet."""
    spreadsheet = {
        'properties': {
            'title': title
        },
        'sheets': [
            {'properties': {'title': 'Test Plan Overview'}},
            {'properties': {'title': 'Test Cases'}},
            {'properties': {'title': 'Test Execution'}},
        ]
    }
    
    response = sheets_service.spreadsheets().create(body=spreadsheet).execute()
    spreadsheet_id = response['spreadsheetId']
    
    sheet_ids = {
        sheet['properties']['title']: sheet['properties']['sheetId']
        for sheet in response['sheets']
    }
        
    make_public(spreadsheet_id)
        
    return spreadsheet_id, sheet_ids

def make_public(spreadsheet_id: str):
    """Make the spreadsheet accessible to anyone with the link."""
    try:
        permission = {
            'type': 'anyone',
            'role': 'writer',
            'allowFileDiscovery': False
        }
        
        drive_service.permissions().create(
            fileId=spreadsheet_id,
            body=permission,
            fields='id'
        ).execute()
        
    except HttpError as error:
        raise Exception(f"Error making spreadsheet public: {str(error)}")

def format_spreadsheet(spreadsheet_id: str, sheet_ids: Dict[str, int]):
    """Apply formatting to the spreadsheet."""
    requests = [
        {
            'repeatCell': {
                'range': {
                    'sheetId': sheet_ids['Test Plan Overview'],
                    'startRowIndex': 0,
                    'endRowIndex': 1,
                },
                'cell': {
                    'userEnteredFormat': {
                        'backgroundColor': {'red': 0.9, 'green': 0.9, 'blue': 0.9},
                        'textFormat': {'bold': True}
                    }
                },
                'fields': 'userEnteredFormat(backgroundColor,textFormat)'
            }
        },
        {
            'repeatCell': {
                'range': {
                    'sheetId': sheet_ids['Test Cases'],
                    'startRowIndex': 0,
                    'endRowIndex': 1,
                },
                'cell': {
                    'userEnteredFormat': {
                        'backgroundColor': {'red': 0.9, 'green': 0.9, 'blue': 0.9},
                        'textFormat': {'bold': True}
                    }
                },
                'fields': 'userEnteredFormat(backgroundColor,textFormat)'
            }
        },
        {
            'autoResizeDimensions': {
                'dimensions': {
                    'sheetId': sheet_ids['Test Cases'],
                    'dimension': 'COLUMNS',
                    'startIndex': 0,
                    'endIndex': 9
                }
            }
        }
    ]
    
    body = {'requests': requests}
    sheets_service.spreadsheets().batchUpdate(
        spreadsheetId=spreadsheet_id,
        body=body
    ).execute()

def populate_test_plan(spreadsheet_id: str, test_plan_data: dict):
    """Populate the spreadsheet with test plan data."""
    # Populate Overview sheet
    overview_data = [
        ['Scope', test_plan_data['overview']['scope']],
        [''],
        ['Objectives'],
        *[[obj] for obj in test_plan_data['overview']['objectives']],
        [''],
        ['Test Environment'],
        *[[env] for env in test_plan_data['overview']['test_environment']]
    ]
    
    sheets_service.spreadsheets().values().update(
        spreadsheetId=spreadsheet_id,
        range='Test Plan Overview!A1',
        valueInputOption='RAW',
        body={'values': overview_data}
    ).execute()
    
    # Populate Test Cases sheet
    test_case_headers = [
        'ID', 'Category', 'Title', 'Description', 'Prerequisites', 
        'Steps', 'Expected Results', 'Priority', 'Status', 'Jira Issue'
    ]
    
    test_case_data = [test_case_headers]
    for tc in test_plan_data['test_cases']:
        test_case_data.append([
            tc['id'],
            tc['category'],
            tc['title'],
            tc['description'],
            tc['prerequisites'],
            '\n'.join(tc['steps']),
            tc['expected_results'],
            tc['priority'],
            tc['status'],
            ''  # Empty Jira Issue cell
        ])
    
    sheets_service.spreadsheets().values().update(
        spreadsheetId=spreadsheet_id,
        range='Test Cases!A1',
        valueInputOption='RAW',
        body={'values': test_case_data}
    ).execute()

def get_test_case_data(spreadsheet_id: str, range: str = 'Test Cases!A:J') -> List[List]:
    """
    Get test case data from the spreadsheet.
    
    Args:
        sheets_service: Google Sheets service instance
        spreadsheet_id (str): The ID of the spreadsheet
        range (str): Optional range to get data from
        
    Returns:
        List[List]: List of rows containing test case data
    """
    result = sheets_service.spreadsheets().values().get(
        spreadsheetId=spreadsheet_id,
        range=range
    ).execute()
    return result.get('values', [])

def update_cell(spreadsheet_id: str, range: str, value: str):
    """
    Update a single cell in the spreadsheet.
    
    Args:
        sheets_service: Google Sheets service instance
        spreadsheet_id (str): The ID of the spreadsheet
        range (str): Cell range in A1 notation
        value (str): New cell value
    """
    sheets_service.spreadsheets().values().update(
        spreadsheetId=spreadsheet_id,
        range=range,
        valueInputOption='RAW',
        body={'values': [[value]]}
    ).execute()

def update_cell_color(spreadsheet_id: str, sheet_id: int, row: int, col: int, color: Dict):
    """
    Update the background color of a cell.
    
    Args:
        sheets_service: Google Sheets service instance
        spreadsheet_id (str): The ID of the spreadsheet
        sheet_id (int): The ID of the specific sheet
        row (int): Row number (1-based)
        col (int): Column number (0-based)
        color (Dict): Color definition {'red': float, 'green': float, 'blue': float}
    """
    request = {
        'repeatCell': {
            'range': {
                'sheetId': sheet_id,
                'startRowIndex': row - 1,
                'endRowIndex': row,
                'startColumnIndex': col,
                'endColumnIndex': col + 1
            },
            'cell': {
                'userEnteredFormat': {
                    'backgroundColor': color
                }
            },
            'fields': 'userEnteredFormat.backgroundColor'
        }
    }
    
    sheets_service.spreadsheets().batchUpdate(
        spreadsheetId=spreadsheet_id,
        body={'requests': [request]}
    ).execute()

def get_sheet_ids(spreadsheet_id: str) -> Dict[str, int]:
    """
    Get sheet IDs for the spreadsheet.
    
    Args:
        sheets_service: Google Sheets service instance
        spreadsheet_id (str): The ID of the spreadsheet
        
    Returns:
        Dict[str, int]: Dictionary mapping sheet names to their IDs
    """
    spreadsheet = sheets_service.spreadsheets().get(
        spreadsheetId=spreadsheet_id
    ).execute()
    return {
        sheet['properties']['title']: sheet['properties']['sheetId'] 
        for sheet in spreadsheet['sheets']
    }

def get_url(spreadsheet_id: str) -> str:
    """
    Get the shareable URL for the spreadsheet.
    
    Args:
        spreadsheet_id (str): The ID of the spreadsheet
        
    Returns:
        str: The shareable URL
    """
    return f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}/edit"

def batch_update_cells(spreadsheet_id: str, updates: List[Dict[str, List]]):
    """
    Update multiple cells in batch.
    
    Args:
        sheets_service: Google Sheets service instance
        spreadsheet_id (str): The ID of the spreadsheet
        updates (List[Dict]): List of updates, each containing 'range' and 'values'
    """
    body = {
        'valueInputOption': 'RAW',
        'data': updates
    }
    
    sheets_service.spreadsheets().values().batchUpdate(
        spreadsheetId=spreadsheet_id,
        body=body
    ).execute()

def batch_update_formatting(spreadsheet_id: str, requests: List[Dict]):
    """
    Apply multiple formatting updates in batch.
    
    Args:
        sheets_service: Google Sheets service instance
        spreadsheet_id (str): The ID of the spreadsheet
        requests (List[Dict]): List of formatting requests
    """
    sheets_service.spreadsheets().batchUpdate(
        spreadsheetId=spreadsheet_id,
        body={'requests': requests}
    ).execute()

sheets_service, drive_service = get_spreadsheet_services(GOOGLE_CREDS_FILE)