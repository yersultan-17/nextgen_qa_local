import os
from typing import Dict, List, Tuple
import anthropic
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import json
import dotenv

dotenv.load_dotenv()

class TestPlanSpreadsheetGenerator:
    def __init__(self, google_creds_file: str, anthropic_api_key: str):
        """
        Initialize the generator with API credentials.
        
        Args:
            google_creds_file (str): Path to Google service account JSON file
            anthropic_api_key (str): Anthropic API key
        """
        self.client = anthropic.Anthropic(api_key=anthropic_api_key)
        self.creds = service_account.Credentials.from_service_account_file(
            google_creds_file,
            scopes=[
                'https://www.googleapis.com/auth/spreadsheets',
                'https://www.googleapis.com/auth/drive'
            ]
        )
        self.sheets_service = build('sheets', 'v4', credentials=self.creds)
        self.drive_service = build('drive', 'v3', credentials=self.creds)
        self.sheet_ids = {}  # Store sheet IDs for reference

    def verify_spreadsheet_access(self, spreadsheet_id: str) -> bool:
        """
        Verify if the service account has access to the spreadsheet.
        
        Args:
            spreadsheet_id (str): The ID of the spreadsheet to check
            
        Returns:
            bool: True if access is verified, False otherwise
        """
        try:
            self.sheets_service.spreadsheets().get(
                spreadsheetId=spreadsheet_id,
                fields='spreadsheetId'
            ).execute()
            return True
        except HttpError as error:
            if error.resp.status == 403:
                return False
            raise error

    def ensure_editor_access(self, spreadsheet_id: str, email: str = None):
        """
        Ensure the service account has editor access to the spreadsheet.
        
        Args:
            spreadsheet_id (str): The ID of the spreadsheet
            email (str, optional): Email address of the service account
        """
        if email is None:
            email = self.creds.service_account_email

        try:
            permissions = self.drive_service.permissions().list(
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
            
            self.drive_service.permissions().create(
                fileId=spreadsheet_id,
                body=permission,
                fields='id',
                sendNotificationEmail=False
            ).execute()

        except HttpError as error:
            raise Exception(f"Error ensuring editor access: {str(error)}")

    def create_spreadsheet(self, title: str) -> Tuple[str, Dict[str, int]]:
        """
        Create a new Google Spreadsheet.
        
        Args:
            title (str): Title for the new spreadsheet
            
        Returns:
            Tuple[str, Dict[str, int]]: Spreadsheet ID and sheet IDs
        """
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
        
        response = self.sheets_service.spreadsheets().create(body=spreadsheet).execute()
        spreadsheet_id = response['spreadsheetId']
        
        # Get sheet IDs
        self.sheet_ids = {}
        for sheet in response['sheets']:
            self.sheet_ids[sheet['properties']['title']] = sheet['properties']['sheetId']
            
        # Make the spreadsheet accessible to anyone with the link
        self.make_public(spreadsheet_id)
            
        return spreadsheet_id, self.sheet_ids

    def make_public(self, spreadsheet_id: str):
        """
        Make the spreadsheet accessible to anyone with the link.
        
        Args:
            spreadsheet_id (str): The ID of the spreadsheet to share
        """
        try:
            permission = {
                'type': 'anyone',
                'role': 'writer',
                'allowFileDiscovery': False
            }
            
            self.drive_service.permissions().create(
                fileId=spreadsheet_id,
                body=permission,
                fields='id'
            ).execute()
            
        except HttpError as error:
            print(f'An error occurred while sharing the spreadsheet: {error}')
            raise error

    def generate_test_plan(self, website_url: str) -> dict:
        """
        Generate test plan using Claude API.
        
        Args:
            website_url (str): URL of the website to test
            
        Returns:
            dict: Generated test plan data
        """
        prompt = f"""
        Create a structured test plan for {website_url} in the following JSON format:
        {{
            "overview": {{
                "scope": "",
                "objectives": [],
                "test_environment": []
            }},
            "test_cases": [
                {{
                    "id": "TC001",
                    "category": "",
                    "title": "",
                    "description": "",
                    "prerequisites": "",
                    "steps": [],
                    "expected_results": "",
                    "priority": "",
                    "status": "Not Started"
                }}
            ]
        }}
        
        Include test cases for:
        - Functional testing
        - UI/UX testing
        - Performance testing
        - Security testing
        - Cross-browser compatibility
        - Mobile responsiveness
        
        Provide at least 3 test cases for each category.
        """
        
        try:
            message = self.client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=4096,
                messages=[{
                    "role": "user",
                    "content": prompt
                }]
            )
            return json.loads(message.content[0].text)
        except Exception as e:
            raise Exception(f"Error generating test plan: {str(e)}")

    def format_spreadsheet(self, spreadsheet_id: str, sheet_ids: Dict[str, int]):
        """
        Apply formatting to the spreadsheet.
        
        Args:
            spreadsheet_id (str): The ID of the spreadsheet
            sheet_ids (Dict[str, int]): Dictionary mapping sheet names to their IDs
        """
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
        self.sheets_service.spreadsheets().batchUpdate(
            spreadsheetId=spreadsheet_id,
            body=body
        ).execute()

    def populate_test_plan(self, spreadsheet_id: str, test_plan_data: dict):
        """
        Populate the spreadsheet with test plan data.
        
        Args:
            spreadsheet_id (str): The ID of the spreadsheet
            test_plan_data (dict): Test plan data to populate
        """
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
        
        self.sheets_service.spreadsheets().values().update(
            spreadsheetId=spreadsheet_id,
            range='Test Plan Overview!A1',
            valueInputOption='RAW',
            body={'values': overview_data}
        ).execute()
        
        # Populate Test Cases sheet
        test_case_headers = [
            'ID', 'Category', 'Title', 'Description', 'Prerequisites', 
            'Steps', 'Expected Results', 'Priority', 'Status'
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
                tc['status']
            ])
        
        self.sheets_service.spreadsheets().values().update(
            spreadsheetId=spreadsheet_id,
            range='Test Cases!A1',
            valueInputOption='RAW',
            body={'values': test_case_data}
        ).execute()

    def get_spreadsheet_url(self, spreadsheet_id: str) -> str:
        """
        Get the shareable URL for the spreadsheet.
        
        Args:
            spreadsheet_id (str): The ID of the spreadsheet
            
        Returns:
            str: The shareable URL
        """
        return f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}/edit"

    def update_test_case_statuses(self, spreadsheet_id: str, updates: List[Dict[str, str]]):
        """
        Update the status of multiple test cases.
        
        Args:
            spreadsheet_id (str): The ID of the spreadsheet
            updates (List[Dict[str, str]]): List of updates, each containing 'id' and 'status'
        """
        try:
            # First verify access
            if not self.verify_spreadsheet_access(spreadsheet_id):
                # Try to ensure editor access
                self.ensure_editor_access(spreadsheet_id)
                
                # Verify access again
                if not self.verify_spreadsheet_access(spreadsheet_id):
                    raise Exception("Unable to obtain necessary permissions for the spreadsheet")

            # Get all test cases from the spreadsheet
            result = self.sheets_service.spreadsheets().values().get(
                spreadsheetId=spreadsheet_id,
                range='Test Cases!A:I'
            ).execute()
            
            values = result.get('values', [])
            if not values:
                raise ValueError("No test cases found in spreadsheet")
                
            # Find the column indices
            headers = values[0]
            try:
                id_col = headers.index('ID')
                status_col = headers.index('Status')
            except ValueError:
                raise ValueError("Required columns 'ID' or 'Status' not found in spreadsheet")
                
            # Create a batch update request
            batch_updates = []
            row_number = 1  # Start after header row
            
            # Create a map of test case IDs to their new statuses
            status_map = {update['id']: update['status'] for update in updates}
            
            # Valid status values for validation
            valid_statuses = {'Not Started', 'In Progress', 'Blocked', 'Failed', 'Passed', 'Skipped'}
            
            # Validate statuses
            invalid_statuses = set(status_map.values()) - valid_statuses
            if invalid_statuses:
                raise ValueError(f"Invalid status values found: {invalid_statuses}. "
                            f"Valid statuses are: {valid_statuses}")
            
            # Find and update each test case
            updated_ids = set()
            for row in values[1:]:  # Skip header row
                row_number += 1
                if not row:  # Skip empty rows
                    continue
                    
                test_case_id = row[id_col]
                if test_case_id in status_map:
                    batch_updates.append({
                        'range': f'Test Cases!{chr(65 + status_col)}{row_number}',
                        'values': [[status_map[test_case_id]]]
                    })
                    updated_ids.add(test_case_id)
            
            # Check if any test case IDs weren't found
            not_found_ids = set(status_map.keys()) - updated_ids
            if not_found_ids:
                raise ValueError(f"Test case IDs not found: {not_found_ids}")
                
            if batch_updates:
                body = {
                    'valueInputOption': 'RAW',
                    'data': batch_updates
                }
                
                # Execute the batch update
                result = self.sheets_service.spreadsheets().values().batchUpdate(
                    spreadsheetId=spreadsheet_id,
                    body=body
                ).execute()
                
                # Store sheet IDs for the spreadsheet if not already stored
                if not self.sheet_ids:
                    spreadsheet = self.sheets_service.spreadsheets().get(
                        spreadsheetId=spreadsheet_id
                    ).execute()
                    self.sheet_ids = {
                        sheet['properties']['title']: sheet['properties']['sheetId'] 
                        for sheet in spreadsheet['sheets']
                    }
                
                # Add color coding based on status
                color_requests = []
                for update in batch_updates:
                    # Extract row number from range
                    row = int(update['range'].split('!')[-1][1:])
                    status = update['values'][0][0]
                    
                    # Define status colors
                    status_colors = {
                        'Passed': {'red': 0.7, 'green': 0.9, 'blue': 0.7},  # Light green
                        'Failed': {'red': 0.9, 'green': 0.7, 'blue': 0.7},  # Light red
                        'Blocked': {'red': 0.9, 'green': 0.85, 'blue': 0.7},  # Light orange
                        'In Progress': {'red': 0.7, 'green': 0.7, 'blue': 0.9},  # Light blue
                        'Skipped': {'red': 0.8, 'green': 0.8, 'blue': 0.8},  # Light gray
                        'Not Started': {'red': 1, 'green': 1, 'blue': 1}  # White
                    }
                    
                    color_requests.append({
                        'repeatCell': {
                            'range': {
                                'sheetId': self.sheet_ids['Test Cases'],
                                'startRowIndex': row - 1,
                                'endRowIndex': row,
                                'startColumnIndex': status_col,
                                'endColumnIndex': status_col + 1
                            },
                            'cell': {
                                'userEnteredFormat': {
                                    'backgroundColor': status_colors.get(status, {'red': 1, 'green': 1, 'blue': 1})
                                }
                            },
                            'fields': 'userEnteredFormat.backgroundColor'
                        }
                    })
                
                if color_requests:
                    self.sheets_service.spreadsheets().batchUpdate(
                        spreadsheetId=spreadsheet_id,
                        body={'requests': color_requests}
                    ).execute()
                
                return f"Updated {len(batch_updates)} test case(s)"
                
        except HttpError as error:
            raise Exception(f"Error updating test cases: {str(error)}")

    def generate_all(self, website_url: str) -> Tuple[dict, str]:
        """
        Generate complete test plan and spreadsheet.
        
        Args:
            website_url (str): URL of the website to test
            
        Returns:
            Tuple[dict, str]: Test plan data and spreadsheet ID
        """
        # Create and populate spreadsheet
        spreadsheet_id, sheet_ids = self.create_spreadsheet(f"Test Plan - {website_url}")
        print(f"Test plan spreadsheet created: {spreadsheet_id}")
        
        # Generate test plan using Claude
        test_plan_data = self.generate_test_plan(website_url)
        print("Test plan generated")
        
        # Format and populate the spreadsheet
        self.format_spreadsheet(spreadsheet_id, sheet_ids)
        print("Spreadsheet formatted")
        self.populate_test_plan(spreadsheet_id, test_plan_data)
        print("Test plan data populated")
        
        return test_plan_data, spreadsheet_id


# Example usage
if __name__ == "__main__":
    # Load environment variables
    anthropic_api_key = os.getenv("ANTHROPIC_API_KEY")
    if not anthropic_api_key:
        raise ValueError("Please set ANTHROPIC_API_KEY environment variable")

    google_creds_file = "empatika-labs-sales-20e446c8764d.json"
    
    # Initialize generator
    generator = TestPlanSpreadsheetGenerator(google_creds_file, anthropic_api_key)
    
    # Generate new test plan
    website_url = "https://www.example.com"
    test_plan_data, spreadsheet_id = generator.generate_all(website_url)
    shareable_url = generator.get_spreadsheet_url(spreadsheet_id)
    print(f"Generated spreadsheet, URL: {shareable_url}")
    
    # Example of updating test case statuses
    status_updates = [
        {'id': 'TC001', 'status': 'Passed'},
        {'id': 'TC002', 'status': 'Failed'},
        {'id': 'TC003', 'status': 'In Progress'}
    ]
    
    try:
        result = generator.update_test_case_statuses(spreadsheet_id, status_updates)
        print(f"Test case statuses updated: {result}")
    except Exception as e:
        print(f"Error updating test cases: {str(e)}")