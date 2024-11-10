import dotenv

dotenv.load_dotenv("../.env")

import os
from typing import Dict, List, Tuple
import anthropic
import json
from datetime import datetime
from firecrawl import FirecrawlApp

from tools.spreadsheet import (
    get_spreadsheet_services, create_spreadsheet, format_spreadsheet,
    populate_test_plan, get_url
)

from tools.mock_data import MOCK_TEST_PLANS

from tools.test_case_manager import update_status, update_statuses


class TestPlanSpreadsheetGenerator:
    def __init__(self, anthropic_api_key: str, firecrawl_api_key: str):
        """
        Initialize the generator with API credentials.
        
        Args:
            google_creds_file (str): Path to Google service account JSON file
            anthropic_api_key (str): Anthropic API key
            firecrawl_api_key (str): Firecrawl API key
        """
        try:
            self.client = anthropic.Anthropic(api_key=anthropic_api_key)
            self.firecrawl = FirecrawlApp(api_key=firecrawl_api_key)
        except Exception as e:
            raise Exception(f"Error initializing TestPlanSpreadsheetGenerator: {str(e)}")

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
                    'formats': ['markdown']
                }
            )
            
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
                    "Feature 2"
                ],
                "workflows": [
                    "Workflow 1",
                    "Workflow 2"
                ],
                "inputs": {{
                    "type": "example value"
                }},
                "test_scenarios": [
                    {{
                        "name": "Scenario name",
                        "description": "What to test",
                        "requirements": ["Requirement 1", "Requirement 2"]
                    }}
                ]
            }}
            """
            
            analysis_message = self.client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=4096,
                messages=[{
                    "role": "user",
                    "content": analysis_prompt
                }]
            )
            
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
            
            test_data = {
                'inputs': analysis_data['inputs'],
                'scenarios': analysis_data['test_scenarios']
            }
            
            # Generate test plan and create spreadsheet
            test_plan_data, spreadsheet_id = self.generate_all(
                website_url=website_url,
                website_description=website_description,
                test_data=test_data
            )
            
            return test_plan_data, spreadsheet_id
            
        except Exception as e:
            raise Exception(f"Error analyzing website and generating test plan: {str(e)}")

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
                        "Step 2"
                    ],
                    "expected_results": "What should happen when test is successful",
                    "priority": "High/Medium/Low",
                    "status": "Not Started"
                }}
            ]
        }}
        
        Important guidelines:
        1. Create at least 3 test cases for each major feature or functionality
        2. Include specific test data and expected results where applicable
        3. Prioritize test cases based on critical functionality
        4. Include edge cases and error conditions
        5. Make steps detailed and actionable
        6. Test cases should be specific to the website's purpose and features
        7. Include security and performance considerations
        8. Consider user experience and accessibility
        9. Make sure that test cases start with navigating to the website URL
        10. If you need personal data for testing, use:
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

    def create_spreadsheet_for_test_plan(self, test_plan_data: dict, website_url: str) -> str:
        """
        Create a Google Spreadsheet for the test plan based on the test plan data.
        
        Args:
            test_plan_data (dict): Test plan data
            website_url (str): URL of the website being tested
            
        Returns:
            str: The ID of the created spreadsheet
        """
        try:
            spreadsheet_id, sheet_ids = create_spreadsheet(
                f"Test Plan - {website_url}"
            )
            format_spreadsheet(spreadsheet_id, sheet_ids)
            populate_test_plan(spreadsheet_id, test_plan_data)
            return spreadsheet_id
        except Exception as e:
            raise Exception(f"Error creating spreadsheet for test plan: {str(e)}")

    def generate_all(self, website_url: str, website_description: str = None, test_data: dict = None) -> Tuple[dict, str]:
        """
        Generate complete test plan and create spreadsheet.
        
        Args:
            website_url (str): URL of the website to test
            website_description (str): Description of the website's purpose and functionality
            test_data (dict): Optional specific test data
            
        Returns:
            Tuple[dict, str]: Test plan data and spreadsheet ID
        """
        try:
            test_plan_data = self.generate_test_plan(website_url, website_description, test_data)
            print("Test plan generated")
            
            spreadsheet_id = self.create_spreadsheet_for_test_plan(test_plan_data, website_url)
            print(f"Spreadsheet created: {get_url(spreadsheet_id)}")
            
            return test_plan_data, spreadsheet_id
        except Exception as e:
            raise Exception(f"Error generating test plan: {str(e)}")


if __name__ == "__main__":
    anthropic_api_key = os.getenv("ANTHROPIC_API_KEY")
    firecrawl_api_key = os.getenv("FIRECRAWL_API_KEY")
    if not anthropic_api_key or not firecrawl_api_key:
        raise ValueError("Please set ANTHROPIC_API_KEY and FIRECRAWL_API_KEY environment variables")

    # Initialize generator
    generator = TestPlanSpreadsheetGenerator(
        anthropic_api_key=anthropic_api_key,
        firecrawl_api_key=firecrawl_api_key
    )

    website_url = "https://app.onsa.ai"

    if website_url in MOCK_TEST_PLANS:
        print(f"Using mock data for website: {website_url}")
        with open(f"mock_data/{MOCK_TEST_PLANS[website_url]}", "r") as f:
            test_plan_data = json.load(f)
    else:
        # Generate test plan and create spreadsheet
        test_plan_data = generator.generate_test_plan(website_url)
    print(f"Test plan data: {test_plan_data}")
    
    spreadsheet_id = generator.create_spreadsheet_for_test_plan(test_plan_data, website_url)
    print(f"Spreadsheet URL: {get_url(spreadsheet_id)}")

    updates = [
        {"id": "TC001", "status": "Passed"},
        {"id": "TC002", "status": "Failed"}
    ]

    # Update test case statuses
    result = update_statuses(spreadsheet_id, updates)
