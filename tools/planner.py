import os
from typing import Dict, List, Tuple
import anthropic
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import json
import dotenv
from datetime import datetime
from tools.jira import create_issue
from firecrawl import FirecrawlApp
from tools.mock_data import MOCK_TEST_PLANS

dotenv.load_dotenv("../.env")

GOOGLE_CREDS_FILE = "tools/empatika-labs-sales-20e446c8764d.json"

class TestPlanSpreadsheetGenerator:
    def __init__(self, google_creds_file: str, anthropic_api_key: str, firecrawl_api_key: str):
        """
        Initialize the generator with API credentials.
        
        Args:
            google_creds_file (str): Path to Google service account JSON file
            anthropic_api_key (str): Anthropic API key
            firecrawl_api_key (str): Firecrawl API key
        """
        # Initialize existing services
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
        self.sheet_ids = {}
        
        # Initialize Firecrawl
        self.firecrawl = FirecrawlApp(api_key=firecrawl_api_key)




class TestPlanSpreadsheetGenerator:
    def __init__(self, google_creds_file: str, anthropic_api_key: str, firecrawl_api_key: str):
        """
        Initialize the generator with API credentials.
        
        Args:
            google_creds_file (str): Path to Google service account JSON file
            anthropic_api_key (str): Anthropic API key
            firecrawl_api_key (str): Firecrawl API key
        """
        # Initialize existing services
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
        self.sheet_ids = {}
        
        # Initialize Firecrawl
        self.firecrawl = FirecrawlApp(api_key=firecrawl_api_key)

    def analyze_website_and_generate_test_plan(self, website_url: str) -> Tuple[dict, str]:
        """
        Analyze website using Firecrawl and generate test plan.
        
        Args:
            website_url (str): URL of the website to analyze
            
        Returns:
            Tuple[dict, str]: Test plan data and spreadsheet ID
        """
        try:
            print(f"Analyzing website: {website_url}")
            
            # Scrape website using Firecrawl
            response = self.firecrawl.scrape_url(
                url=website_url,
                params={
                    'formats': ['markdown'],  # Get markdown format
                }
            )
            
            # Extract website content from Firecrawl response
            website_content = response.get('markdown', '')
            
            # Generate website analysis using Claude
            analysis_prompt = f"""
            Analyze the following website content and create a structured analysis for test plan generation.
            
            Website URL: {website_url}
            
            Content:
            {website_content}
            
            Please analyze this content and provide a structured response in JSON format that includes:
            1. Website purpose and main features
            2. User interactions and workflows
            3. Input/output requirements
            4. Integration points
            5. Key functionality areas
            6. Potential test scenarios
            
            Format the response as:
            {{
                "description": "Detailed website description",
                "features": [
                    "Feature 1",
                    "Feature 2",
                    ...
                ],
                "workflows": [
                    "Workflow 1",
                    "Workflow 2",
                    ...
                ],
                "inputs": {{
                    "type": "example value",
                    ...
                }},
                "test_scenarios": [
                    {{
                        "name": "Scenario name",
                        "description": "What to test",
                        "requirements": ["Requirement 1", "Requirement 2"]
                    }},
                    ...
                ]
            }}
            """
            
            # Get analysis from Claude
            analysis_message = self.client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=4096,
                messages=[{
                    "role": "user",
                    "content": analysis_prompt
                }]
            )
            
            # Parse the analysis response
            analysis_data = json.loads(analysis_message.content[0].text)
            
            # Format description for test plan
            website_description = f"""
            Website: {website_url}
            
            Purpose and Description:
            {analysis_data['description']}
            
            Key Features:
            {chr(10).join('- ' + feature for feature in analysis_data['features'])}
            
            Main Workflows:
            {chr(10).join('- ' + workflow for workflow in analysis_data['workflows'])}
            
            Test Scenarios:
            {chr(10).join(f"- {scenario['name']}: {scenario['description']}" for scenario in analysis_data['test_scenarios'])}
            """
            
            # Create test data structure
            test_data = {
                'inputs': analysis_data['inputs'],
                'scenarios': analysis_data['test_scenarios']
            }
            
            # Generate test plan using the analyzed information
            test_plan_data, spreadsheet_id = self.generate_all(
                website_url=website_url,
                website_description=website_description,
                test_data=test_data
            )
            
            return test_plan_data, spreadsheet_id
            
        except Exception as e:
            raise Exception(f"Error analyzing website and generating test plan: {str(e)}")


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

    def generate_test_plan(self, website_url: str, website_description: str = None, test_data: dict = None) -> dict:
        """
        Generate test plan using Claude API with specific test data.
        
        Args:
            website_url (str): URL of the website to test
            website_description (str): Description of the website's purpose and functionality
            test_data (dict): Optional specific test data including test inputs and expected results
            
        Returns:
            dict: Generated test plan data
        """
        context = f"""
        Create a comprehensive test plan for: {website_url}

        Website Description:
        {website_description or 'A web application that needs testing across functionality, performance, security, and user experience aspects.'}

        Test Data Examples:
        {json.dumps(test_data, indent=2) if test_data else 'Generate appropriate test data based on the website description.'}
        """

        prompt = f"""
        Based on the above context, create a structured test plan in the following JSON format.
        Consider all aspects of testing including but not limited to:
        - Core functionality testing specific to the website's purpose
        - User interface and experience testing
        - Performance testing
        - Security testing
        - Error handling
        - Cross-browser compatibility
        - Mobile responsiveness
        - Integration testing where applicable
        - Edge cases and boundary testing
        
        Return the response in this exact JSON format:
        {{
            "overview": {{
                "scope": "Automated testing of {website_url}'s core functionality and user experience",
                "objectives": [
                    // Generate 5-7 specific objectives based on the website description
                ],
                "test_environment": [
                    "Chrome Browser Version 120+",
                    "Firefox Browser Version 120+",
                    "Safari Browser Version 17+",
                    "Mobile Chrome on iOS 17+",
                    "Mobile Chrome on Android 14+"
                ]
            }},
            "test_cases": [
                {{
                    "id": "TC001",
                    "category": "Category Name",
                    "title": "Test Case Title",
                    "description": "Detailed description of what is being tested",
                    "prerequisites": "Required setup or conditions",
                    "steps": [
                        "Step 1",
                        "Step 2",
                        "..."
                    ],
                    "expected_results": "What should happen when test is successful",
                    "priority": "High/Medium/Low",
                    "status": "Not Started"
                }}
            ]
        }}
        
        Important guidelines for generating test cases:
        1. Create at least 3 test cases for each major feature or functionality
        2. Include specific test data and expected results where applicable
        3. Prioritize test cases based on critical functionality
        4. Include edge cases and error conditions
        5. Make steps detailed and actionable
        6. Test cases should be specific to the website's purpose and features
        7. Include security and performance considerations
        8. Consider user experience and accessibility
        9. Make sure that test cases start with navigating to the website URL.
        10. If you need personal data for testing, use the following person info:
        - Name: Bayram Annakov
        - LinkedIn: https://www.linkedin.com/in/bayramannakov
        """
        
        try:
            message = self.client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=4096,
                messages=[
                    {"role": "user", "content": context},
                    {"role": "assistant", "content": "I understand you want me to create a test plan for this website. I'll generate appropriate test cases based on the website's description and purpose."},
                    {"role": "user", "content": prompt}
                ]
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
        
        # Populate Test Cases sheet with Jira Issue column
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
        
        self.sheets_service.spreadsheets().values().update(
            spreadsheetId=spreadsheet_id,
            range='Test Cases!A1',
            valueInputOption='RAW',
            body={'values': test_case_data}
        ).execute()

    def create_jira_issues_for_failures(self, spreadsheet_id: str, failed_rows: List[List]) -> List[Dict]:
        """
        Create Jira issues for failed test cases.

        Args:
            spreadsheet_id (str): The ID of the spreadsheet
            failed_rows (List[List]): List of rows containing failed test case data
            
        Returns:
            List[Dict]: List of created Jira issues
        """
        created_issues = []

        # Get headers to find column indices
        result = self.sheets_service.spreadsheets().values().get(
            spreadsheetId=spreadsheet_id,
            range='Test Cases!A1:J1'
        ).execute()

        headers = result['values'][0]
        id_col = headers.index('ID')
        title_col = headers.index('Title')
        desc_col = headers.index('Description')
        steps_col = headers.index('Steps')
        expected_col = headers.index('Expected Results')
        jira_col = headers.index('Jira Issue') if 'Jira Issue' in headers else len(headers)

        for row in failed_rows:
            # Skip if already has a Jira issue
            if len(row) > jira_col and row[jira_col]:
                continue
                
            # Create Jira issue summary
            summary = f"Failed Test Case: {row[title_col]} ({row[id_col]})"
            
            # Create detailed description
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
        - Spreadsheet: {self.get_spreadsheet_url(spreadsheet_id)}
        """
            
            try:
                # Create Jira issue
                jira_response = create_issue(summary, description)
                
                # Debug print
                print(f"Jira response for {row[id_col]}: {jira_response}")
                
                if jira_response:
                    # Add created issue to our list
                    created_issues.append({
                        'test_case_id': row[id_col],
                        'jira_key': jira_response['key'],  # Convert response to string for now
                        'summary': summary
                    })
                    
                    # Update spreadsheet with Jira reference
                    row_num = failed_rows.index(row) + 2
                    self.sheets_service.spreadsheets().values().update(
                        spreadsheetId=spreadsheet_id,
                        range=f'Test Cases!{chr(65 + jira_col)}{row_num}',
                        valueInputOption='RAW',
                        body={'values': [["https://nextgen-qa.atlassian.net/jira/software/c/projects/NQ/issues/"+jira_response["key"]]]}  # Convert response to string
                    ).execute()
                    
                    print(f"Created Jira issue for test case {row[id_col]}")
                        
            except Exception as e:
                print(f"Error creating Jira issue for test case {row[id_col]}: {str(e)}")
                continue
                
        return created_issues

    def update_test_case_statuses(self, spreadsheet_id: str, updates: List[Dict[str, str]]):
        """
        Update the status of multiple test cases and create Jira issues for failures.
        
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
                range='Test Cases!A:J'  # Include Jira Issue column
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
            failed_rows = []  # Track failed test cases

            for row in values[1:]:  # Skip header row
                row_number += 1
                if not row:  # Skip empty rows
                    continue
                    
                test_case_id = row[id_col]
                if test_case_id in status_map:
                    new_status = status_map[test_case_id]
                    batch_updates.append({
                        'range': f'Test Cases!{chr(65 + status_col)}{row_number}',
                        'values': [[new_status]]
                    })
                    updated_ids.add(test_case_id)
                    
                    # If status is Failed, add to failed_rows
                    if new_status == 'Failed':
                        failed_rows.append(row)
            
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

                # Create Jira issues for failed test cases
                if failed_rows:
                    print("Creating Jira issues for failed test cases...")
                    created_issues = self.create_jira_issues_for_failures(spreadsheet_id, failed_rows)
                    
                    if created_issues:
                        print(f"\nCreated {len(created_issues)} Jira issues:")
                        for issue in created_issues:
                            print(f"- {issue['test_case_id']}: {issue['jira_key']} - {issue['summary']}")
                
                return f"Updated {len(batch_updates)} test case(s)"
                
        except HttpError as error:
            raise Exception(f"Error updating test cases: {str(error)}")

    def get_spreadsheet_url(self, spreadsheet_id: str) -> str:
        """
        Get the shareable URL for the spreadsheet.
        
        Args:
            spreadsheet_id (str): The ID of the spreadsheet
            
        Returns:
            str: The shareable URL
        """
        return f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}/edit"

    
    def create_spreadsheet_for_test_plan(self, test_plan_data: dict, website_url: str) -> str:
        """
        Create a Google Spreadsheet for the test plan based on the test plan data.
        
        Args:
            test_plan_data (dict): Test plan data
            website_url (str): URL of the website being tested
            
        Returns:
            str: The ID of the created spreadsheet
        """
        # Create a new spreadsheet
        spreadsheet_id, sheet_ids = self.create_spreadsheet(f"Test Plan - {website_url}")
        
        # Format and populate the spreadsheet
        self.format_spreadsheet(spreadsheet_id, sheet_ids)
        print("Spreadsheet formatted")
        self.populate_test_plan(spreadsheet_id, test_plan_data)
        print("Test plan data populated")
        
        return spreadsheet_id
    
    def generate_all(self, website_url: str, website_description: str = None, test_data: dict = None) -> Tuple[dict, str]:
        """
        Generate complete test plan and spreadsheet.
        
        Args:
            website_url (str): URL of the website to test
            website_description (str): Description of the website's purpose and functionality
            test_data (dict): Optional specific test data
            
        Returns:
            Tuple[dict, str]: Test plan data and spreadsheet ID
        """

        # Generate test plan using Claude
        test_plan_data = self.generate_test_plan(website_url, website_description, test_data)
        print("Test plan generated")
        
        # Create a spreadsheet for the test plan
        spreadsheet_id = self.create_spreadsheet_for_test_plan(test_plan_data, website_url)
        
        return test_plan_data, spreadsheet_id
    
def get_plan_data(website_url: str):
    # Load environment variables
    anthropic_api_key = os.getenv("ANTHROPIC_API_KEY")
    firecrawl_api_key = os.getenv("FIRECRAWL_API_KEY")
    if not anthropic_api_key or not firecrawl_api_key:
        raise ValueError("Please set ANTHROPIC_API_KEY and FIRECRAWL_API_KEY environment variables")

    google_creds_file = GOOGLE_CREDS_FILE

    # Initialize generator with all necessary API keys
    generator = TestPlanSpreadsheetGenerator(
        google_creds_file=google_creds_file,
        anthropic_api_key=anthropic_api_key,
        firecrawl_api_key=firecrawl_api_key
    )

    if website_url in MOCK_TEST_PLANS:
        print(f"Using mock data for website: {website_url}")
        path_to_mock_data = MOCK_TEST_PLANS[website_url]
        with open(path_to_mock_data, "r") as file:
            test_plan_data = json.load(file)
    else:
        test_plan_data = generator.generate_test_plan(website_url)

    spreadsheet_id = generator.create_spreadsheet_for_test_plan(test_plan_data, website_url)
    
    return test_plan_data, spreadsheet_id

# Example usage
if __name__ == "__main__":
    website_url = "https://app.onsa.ai"
    test_plan_data, spreadsheet_id = get_plan_data(website_url)
    
    # # Get the shareable URL
    # shareable_url = generator.get_spreadsheet_url(spreadsheet_id)
    # print(f"\nTest plan generated: {shareable_url}")
    
    # # Update test case statuses
    # updates = [
    #     {"id": "TC001", "status": "Failed"},
    #     {"id": "TC002", "status": "Passed"},
    #     {"id": "TC003", "status": "In Progress"}
    # ]

    # try:
    #     result = generator.update_test_case_statuses(spreadsheet_id, updates)
    #     print(f"Test case statuses updated: {result}")
    # except Exception as e:
    #     print(f"Error updating test cases: {str(e)}")


    
