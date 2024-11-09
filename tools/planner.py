import os
import anthropic
from typing import Dict, List

class TestPlanGenerator:
    def __init__(self, api_key: str):
        """
        Initialize the TestPlanGenerator with your Claude API key.
        
        Args:
            api_key (str): Your Anthropic API key
        """
        self.client = anthropic.Anthropic(api_key=api_key)
        
    def generate_test_plan(self, website_url: str, additional_context: str = "") -> str:
        """
        Generate a comprehensive test plan for a given website using Claude.
        
        Args:
            website_url (str): The URL of the website to test
            additional_context (str): Any additional requirements or context
            
        Returns:
            str: The generated test plan
        """
        prompt = f"""
        Please create a comprehensive test plan for the website: {website_url}
        
        Additional context: {additional_context}
        
        The test plan should include:
        1. Scope and objectives
        2. Test environment requirements
        3. Functional testing scenarios
        4. UI/UX testing scenarios
        5. Performance testing scenarios
        6. Security testing considerations
        7. Cross-browser compatibility testing
        8. Mobile responsiveness testing
        9. Test data requirements
        10. Test execution schedule
        
        For each testing category, please provide:
        - Specific test cases
        - Expected results
        - Priority levels
        - Any prerequisites
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
            return message.content[0].text
            
        except Exception as e:
            return f"Error generating test plan: {str(e)}"
    
    def generate_specific_test_cases(self, feature: str, requirements: Dict) -> str:
        """
        Generate detailed test cases for a specific feature.
        
        Args:
            feature (str): The feature to test
            requirements (Dict): Dictionary containing feature requirements
            
        Returns:
            str: Detailed test cases for the feature
        """
        prompt = f"""
        Please create detailed test cases for the following feature: {feature}
        
        Requirements:
        {requirements}
        
        Please include:
        1. Prerequisite conditions
        2. Test steps
        3. Expected results
        4. Edge cases
        5. Negative testing scenarios
        6. Test data requirements
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
            return message.content[0].text
            
        except Exception as e:
            return f"Error generating test cases: {str(e)}"

def main():
    # Example usage
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise ValueError("Please set ANTHROPIC_API_KEY environment variable")
    
    test_generator = TestPlanGenerator(api_key)
    
    # Generate full test plan
    website = "https://example.com"
    context = "This is an e-commerce website with user authentication, product catalog, and checkout functionality"
    test_plan = test_generator.generate_test_plan(website, context)
    print("Full Test Plan:")
    print(test_plan)
    
    # Generate specific feature test cases
    feature = "Shopping Cart"
    requirements = {
        "add_to_cart": "Users should be able to add multiple items",
        "remove_from_cart": "Users should be able to remove items",
        "update_quantity": "Users should be able to update item quantities",
        "save_for_later": "Users should be able to save items for later"
    }
    feature_tests = test_generator.generate_specific_test_cases(feature, requirements)
    print("\nFeature-specific Test Cases:")
    print(feature_tests)

if __name__ == "__main__":
    main()