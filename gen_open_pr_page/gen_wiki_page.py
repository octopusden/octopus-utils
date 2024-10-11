import csv
import requests
import json
import html
from argparse import ArgumentParser


def read_csv_files(csv_files):
    all_data = []
    for file in csv_files:
        with open(file, mode='r', newline='', encoding='utf-8') as f:
            reader = csv.reader(f)
            headers = next(reader)  # Get the headers
            for row in reader:
                all_data.append(row)
    return headers, all_data


def get_existing_page(confluence_url, username, password, space_key, page_title):
    # Fetch the page based on the title and space key
    response = requests.get(
        f"{confluence_url}/rest/api/content?title={page_title}&spaceKey={space_key}&expand=version",
        auth=(username, password)
    )

    if response.status_code == 200:
        pages = response.json().get('results', [])
        if pages:
            return pages[0]  # Return the first matching page
    return None  # Return None if no page found


def create_confluence_page(confluence_url, username, password, space_key, page_title, parent_page_id, headers, data):
    # Find indices for Pull Request Title and Pull Request URL
    title_index = headers.index("Pull Request Title")
    url_index = headers.index("Pull Request URL")

    # Construct the table HTML
    table_html = "<table><tr>" + "".join(f"<th>{header}</th>" for header in headers if header not in ["Pull Request Title", "Pull Request URL"]) + "<th>Pull Request</th></tr>"
    for row in data:
        # Create a hyperlink for the Pull Request column
        pull_request_title = html.escape(row[title_index])
        pull_request_url = row[url_index]
        pull_request_link = f'<a href="{pull_request_url}">{pull_request_title}</a>'

        # Add the row to the table without the original Pull Request Title and URL columns
        table_html += "<tr>" + "".join(f"<td>{cell}</td>" for i, cell in enumerate(row) if i not in [title_index, url_index]) + f"<td>{pull_request_link}</td></tr>"
    table_html += "</table>"

    # Construct the page content
    page_content = {
        "type": "page",
        "title": page_title,
        "ancestors": [{"id": parent_page_id}],
        "space": {"key": space_key},
        "body": {
            "storage": {
                "value": table_html,
                "representation": "storage"
            }
        }
    }

    # Check if the page exists
    existing_page = get_existing_page(confluence_url, username, password, space_key, page_title)

    if existing_page:
        # Debugging output
        print("Existing page found:", json.dumps(existing_page, indent=4))

        # Check if the version key exists
        if 'version' in existing_page:
            page_content["version"] = {
                "number": existing_page['version']['number'] + 1,  # Increment the version number
                "minorEdit": True
            }
            # Update the page using the existing page ID
            response = requests.put(
                f"{confluence_url}/rest/api/content/{existing_page['id']}",
                data=json.dumps({**page_content, "id": existing_page['id']}),  # Merging page content with existing ID
                headers={"Content-Type": "application/json"},
                auth=(username, password)
            )
            action = "updated"
        else:
            print("Warning: Existing page does not have a version number. Unable to update.")
            return
    else:
        # If it doesn't exist, create a new page
        response = requests.post(
            f"{confluence_url}/rest/api/content/",
            data=json.dumps(page_content),
            headers={"Content-Type": "application/json"},
            auth=(username, password)
        )
        action = "created"

    if response.status_code in (200, 201):
        print(f"Page {action} successfully!")
    else:
        print(f"Failed to {action} page: {response.status_code} - {response.text}")


def main():
    parser = ArgumentParser(description="Create or update a Confluence page with data from CSV files.")
    parser.add_argument("confluence_url", help="Confluence URL (on-premise instance)")
    parser.add_argument("username", help="Confluence username")
    parser.add_argument("password", help="Confluence password")
    parser.add_argument("space_key", help="Wiki space key")
    parser.add_argument("page_title", help="Title of the wiki page")
    parser.add_argument("parent_page_id", help="ID of the parent page")
    parser.add_argument("csv_files", nargs='+', help="CSV files to read data from")

    args = parser.parse_args()

    headers, data = read_csv_files(args.csv_files)

    create_confluence_page(args.confluence_url, args.username, args.password, args.space_key, args.page_title, args.parent_page_id, headers, data)


if __name__ == "__main__":
    main()
