#!/usr/bin/env python3

import requests
from requests.auth import HTTPBasicAuth
import argparse
from datetime import datetime
import csv


# Function to convert Unix timestamp to a human-readable format
def format_timestamp(timestamp):
    if isinstance(timestamp, int):  # Check if timestamp is valid
        return datetime.utcfromtimestamp(timestamp / 1000).strftime('%Y-%m-%d %H:%M:%S')
    return "Unknown Date"


# Function to get all open pull requests for a list of projects on an on-premise Bitbucket instance
def get_open_pull_requests(bitbucket_url, projects, username, app_password):
    pull_requests = []

    for project in projects:
        # Construct the URL for each project using the on-premise Bitbucket server URL
        project_url = f"{bitbucket_url}/rest/api/1.0/projects/{project}/repos?limit=50"

        try:
            # Make an authenticated request to the API to get repositories for the project
            response = requests.get(project_url, auth=HTTPBasicAuth(username, app_password))
            response.raise_for_status()  # Check for HTTP errors

            # Parse the response JSON to get repositories
            data = response.json()
            for repo in data['values']:
                repo_slug = repo['slug']
                project_key = repo['project']['key']

                # Fetch open pull requests for each repository
                pull_request_url = f"{bitbucket_url}/rest/api/1.0/projects/{project_key}/repos/{repo_slug}/pull-requests?state=OPEN&limit=50"
                pr_response = requests.get(pull_request_url, auth=HTTPBasicAuth(username, app_password))
                pr_response.raise_for_status()
                pr_data = pr_response.json()

                # Add the open pull requests to the list
                for pr in pr_data['values']:
                    # Author and merge information
                    author_info = pr.get('author', {})
                    display_name = author_info.get('displayName') or author_info.get('user', {}).get('displayName') or 'Unknown Author'
                    created_on = format_timestamp(pr.get('createdDate', 'Unknown Date'))
                    ready_to_merge = "Unknown"

                    # Construct the pull request URL
                    pr_id = pr['id']
                    pr_url = f"{bitbucket_url}/projects/{project_key}/repos/{repo_slug}/pull-requests/{pr_id}"

                    pull_requests.append({
                        'project': project_key,
                        'repository': repo_slug,
                        'pull_request': pr['title'],
                        'author': display_name,
                        'created_on': created_on,
                        'pull_request_url': pr_url,
                        'ready_to_merge': ready_to_merge
                    })

        except requests.exceptions.RequestException as e:
            print(f"Failed to retrieve pull requests for project {project}: {e}")
        except KeyError as ke:
            print(f"Key error encountered: {ke}. Full response: {pr_data}")

    return pull_requests


# Main function to handle command-line arguments
def main():
    # Set up argument parser
    parser = argparse.ArgumentParser(description="Fetch open pull requests for a list of Bitbucket projects on an on-premise server.")

    # Add arguments
    parser.add_argument('-b', '--bitbucket_url', required=True, help="Bitbucket server URL (e.g., https://bitbucket.company.com)")
    parser.add_argument('-p', '--projects', nargs='+', required=True, help="List of Bitbucket projects")
    parser.add_argument('-u', '--username', required=True, help="Bitbucket username")
    parser.add_argument('-a', '--app_password', required=True, help="Bitbucket app password or personal access token")

    # Parse the arguments
    args = parser.parse_args()

    # Get open pull requests
    open_prs = get_open_pull_requests(args.bitbucket_url, args.projects, args.username, args.app_password)

    # Write the results to a CSV file with a comma delimiter
    with open('bb-pr.csv', 'w', newline='', encoding='utf-8') as csvfile:
        fieldnames = ['Project', 'Repository', 'Pull Request Title', 'Author', 'Created Time', 'Pull Request URL', 'Ready to Merge']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames, delimiter=',')

        writer.writeheader()  # Write the header
        for pr in open_prs:
            writer.writerow({
                'Project': pr['project'],
                'Repository': pr['repository'],
                'Pull Request Title': pr['pull_request'],
                'Author': pr['author'],
                'Created Time': pr['created_on'],
                'Pull Request URL': pr['pull_request_url'],
                'Ready to Merge': pr['ready_to_merge'],
            })

    print("Data written to bb-pr.csv")


# Entry point for the script
if __name__ == "__main__":
    main()