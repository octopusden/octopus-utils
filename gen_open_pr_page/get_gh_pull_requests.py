#!/usr/bin/env python3

import requests
import argparse
from datetime import datetime
import csv
import time
import json

# GitHub API base URL
API_URL = "https://api.github.com"


# Function to get repositories of the user
def get_user_repos(username, headers):
    repos_url = f"{API_URL}/users/{username}/repos"
    response = requests.get(repos_url, headers=headers)
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Error fetching repositories: {response.status_code}")
        return []


# Function to get open pull requests for a repository
def get_open_pull_requests(owner, repo, headers):
    pulls_url = f"{API_URL}/repos/{owner}/{repo}/pulls"
    params = {'state': 'open'}
    response = requests.get(pulls_url, headers=headers, params=params)
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Error fetching pull requests for {repo}: {response.status_code}")
        return []


# Function to check mergeability of a pull request, with retries
def get_mergeable_status(owner, repo, pr_number, headers):
    pr_url = f"{API_URL}/repos/{owner}/{repo}/pulls/{pr_number}"

    for _ in range(3):  # Try up to 3 times
        response = requests.get(pr_url, headers=headers)
        if response.status_code == 200:
            pr_data = response.json()
            # Check for mergeable and mergeable_state fields
            mergeable = pr_data.get('mergeable')
            mergeable_state = pr_data.get('mergeable_state')
            if mergeable is not None and mergeable_state is not None:
                return mergeable, mergeable_state
        time.sleep(2)  # Wait for 2 seconds before trying again
    return None, None  # Return None if mergeability couldn't be determined


# Function to convert ISO date to a human-readable format
def human_readable_date(iso_date_str):
    date_obj = datetime.strptime(iso_date_str, '%Y-%m-%dT%H:%M:%SZ')
    return date_obj.strftime('%Y-%m-%d %H:%M:%S')


# Function to list all open pull requests for a user across all repositories
def list_open_pull_requests(username, headers):
    repos = get_user_repos(username, headers)
    print(json.dumps(repos))

    # Open the CSV file for writing
    with open('gh-pr.csv', mode='w', newline='', encoding='utf-8') as file:
        writer = csv.writer(file, delimiter=',')  # Use comma as the delimiter

        # Write the header
        writer.writerow(["Project", "Repository", "Pull Request Title", "Author", "Created Time", "Pull Request URL", "Ready to Merge"])

        for repo in repos:
            repo_name = repo['name']
            owner = repo['owner']['login']
            open_pulls = get_open_pull_requests(owner, repo_name, headers)
            for pr in open_pulls:
                pr_number = pr['number']
                creation_date = human_readable_date(pr['created_at'])
                pr_url = pr['html_url']  # Get the pull request URL

                # Get mergeable status with retries
                mergeable, mergeable_state = get_mergeable_status(owner, repo_name, pr_number, headers)
                if mergeable is None or mergeable_state is None:
                    ready_to_merge = 'Unknown'
                else:
                    # Determine if the pull request is ready to merge based on both mergeable and mergeable_state
                    if mergeable and mergeable_state == 'clean':
                        ready_to_merge = 'Yes'
                    elif mergeable_state == 'blocked':
                        ready_to_merge = 'Blocked'
                    else:
                        ready_to_merge = 'No'

                # Write the data row
                writer.writerow([username, repo_name, pr['title'], pr['user']['login'], creation_date, pr_url, ready_to_merge])


# Main method to handle command-line arguments and trigger the process
def main():
    parser = argparse.ArgumentParser(description="List all open pull requests for a GitHub user across all repositories.")
    parser.add_argument("username", help="GitHub username whose repositories you want to query")
    parser.add_argument("token", help="GitHub personal access token or password")

    args = parser.parse_args()

    # Set up headers with the token from command-line arguments
    headers = {
        'Authorization': f'token {args.token}',
        'Accept': 'application/vnd.github.v3+json'
    }

    # Call the function to list open pull requests
    list_open_pull_requests(args.username, headers)


if __name__ == "__main__":
    main()
