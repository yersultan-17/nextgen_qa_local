import os
from typing import Dict, List, Tuple
import anthropic
from google.oauth2.credentials import Credentials
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import json

class TestPlanSpreadsheetGenerator:
    def __init__(self, anthropic_api_key: str, google_creds_file: str):
        """
        Initialize the generator with API credentials.
        
        Args:
            anthropic_api_key (str): Anthropic API key
            google_creds_file (str): Path to Google service account JSON file
        """
        self.client = anthropic.Anthropic(api_key=anthropic_api_key)
        self.creds = service_account.Credentials.from_service_account_file(
            google_creds_file,
            scopes=[
                'https://www.googleapis.com/auth/spreadsheets',
                'https://www.googleapis.com/auth/drive'  # Added Drive scope for sharing
            ]
        )
        self.sheets_service = build('sheets', 'v4', credentials=self.creds)
        self.drive_service = build('drive', 'v3', credentials=self.creds)  # Added Drive service

    def create_spreadsheet(self, title: str) -> Tuple[str, Dict[str, int]]:
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
        
        response = self.sheets_service.spreadsheets().create(body=spreadsheet).execute()
        spreadsheet_id = response['spreadsheetId']
        
        # Get sheet IDs
        sheet_ids = {}
        for sheet in response['sheets']:
            sheet_ids[sheet['properties']['title']] = sheet['properties']['sheetId']
            
        # Make the spreadsheet accessible to anyone with the link
        self.make_public(spreadsheet_id)
            
        return spreadsheet_id, sheet_ids

    def make_public(self, spreadsheet_id: str):
        """
        Make the spreadsheet accessible to anyone with the link.
        
        Args:
            spreadsheet_id (str): The ID of the spreadsheet to share
        """
        try:
            # Create a new permission for anyone with the link to view
            permission = {
                'type': 'anyone',
                'role': 'reader',
                'allowFileDiscovery': False  # Prevents the file from appearing in public search
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
        """Generate test plan using Claude API."""
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
            # Add column auto-resize requests
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
        return f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}/view"

def generate_all(website_url:str):
    # Example usage
    anthropic_api_key = os.getenv("ANTHROPIC_API_KEY")
    if not anthropic_api_key:
        raise ValueError("Please set ANTHROPIC_API_KEY environment variable")
    
    # Path to your Google service account JSON file
    google_creds_file = "empatika-labs-sales-20e446c8764d.json"
    
    generator = TestPlanSpreadsheetGenerator(anthropic_api_key, google_creds_file)

    # Create and populate spreadsheet
    spreadsheet_id, sheet_ids = generator.create_spreadsheet(f"Test Plan - {website_url}")
    print(f"Test plan spreadsheet created: {spreadsheet_id}")
    
    # Generate test plan using Claude
    test_plan_data = generator.generate_test_plan(website_url)
    print("Test plan generated")
    
    # Format and populate the spreadsheet
    generator.format_spreadsheet(spreadsheet_id, sheet_ids)
    print("Spreadsheet formatted")
    generator.populate_test_plan(spreadsheet_id, test_plan_data)
    print("Test plan data populated")
    
    # Get the shareable URL
    shareable_url = generator.get_spreadsheet_url(spreadsheet_id)
    print(f"Test plan spreadsheet created and shared: {shareable_url}")

    return test_plan_data, shareable_url

if __name__ == "__main__":
    website_url = "https://www.example.com"
    generate_all(website_url)