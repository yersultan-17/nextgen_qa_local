import dotenv

dotenv.load_dotenv()

import os
from atlassian import Jira

# Replace with your Jira instance details
jira_server = "https://nextgen-qa.atlassian.net"  # Jira server URL
jira_user = "bayram.annakov@gmail.com"  # Your Jira email
jira_api_token = os.environ["JIRA_TOKEN"]  # Your Jira API token
# Initialize the Jira client
jira = Jira(
    url=jira_server,
    username=jira_user,
    password=jira_api_token,
    cloud=True,  # Set to True if using Jira Cloud
)
def create_issue(summary, description):
    # Define the issue fields
    issue_fields = {
        "fields": {
            "project": {"key": "NQ"},  # Replace 'PROJ' with your project key
            "summary": summary,
            "description": description,
            "issuetype": {"name": "Bug"},
        }
    }
    # Create the issue
    try:
        new_issue = jira.issue_create(fields=issue_fields["fields"])
        print(f"Issue {new_issue} created successfully.")
        return new_issue
    except Exception as e:
        print(f"An error occurred: {e}")
create_issue("Test Issue", "This is a test issue created via the Jira API.")