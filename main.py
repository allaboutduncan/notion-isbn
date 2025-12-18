import requests
from datetime import datetime
from dateutil import parser
import time
import schedule
from PIL import Image, ImageFilter
import re
import urllib
import logging
import boto3
from botocore.exceptions import ClientError
import os
from bs4 import BeautifulSoup
import textwrap
from pushbullet import Pushbullet


# Constants and Configuration
SERVICE_NAME = "Notion Books"
NOTION_TOKEN = os.getenv("NOTION_TOKEN")
DATABASE_ID = os.getenv("NOTION_DATABASE_ID")
USE_PUSHBULLET = os.getenv("USE_PUSHBULLET", "no")  # Default to 'no' if USE_PUSHBULLET is not set
USE_AWS = os.getenv("USE_AWS", "no")  # Default to 'no' if USE_AWS is not set

GOOGLE_API_KEY = os.getenv("GoogleAPIKey")

if USE_PUSHBULLET.lower() == "yes":
    PB_TOKEN = os.getenv("PB_TOKEN")
    pb = Pushbullet(PB_TOKEN)


if USE_AWS.lower() == "yes":
    BUCKET = os.getenv("AWS_BUCKET")
    AWS_REGION = os.getenv("AWS_REGION", "us-east-2")  # Default to us-east-2 if not set


NOTION_HEADERS = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Content-Type": "application/json",
    "Notion-Version": "2022-06-28",
}


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()],
)


def send_push(subject, message):
    if os.getenv("USE_PUSHBULLET", "").lower() == "yes":
        push = pb.push_note(subject, message)


def remove_html(input_string):
    soup = BeautifulSoup(input_string, "html.parser")
    return soup.get_text()


def upload_file(file_name, object_name, bucket_folder):
    s3_client = boto3.client("s3", region_name=AWS_REGION)
    object_name = f"{bucket_folder}{object_name or os.path.basename(file_name)}"

    try:
        s3_client.upload_file(file_name, BUCKET, object_name)
    except ClientError as e:
        logging.error(e)
        return False
    return True


# Updated get_book function to use both Google Books API and OpenLibrary API
def get_book(isbn):
    isbn = str(isbn)
    # Try Google Books API first
    base_url_google = f"https://www.googleapis.com/books/v1/volumes?country=US&q=isbn:{isbn}&key={GOOGLE_API_KEY}"
    try:
        response = requests.get(base_url_google)
        response.raise_for_status()
        book_data = response.json()

        if book_data["totalItems"] > 0:
            book_info = book_data["items"][0]["volumeInfo"]
            logging.info(f"Found {book_info.get('title', 'Unknown Title')} using Google Books API")
            # Standardize the data
            standardized_data = {
                'title': book_info.get('title', ''),
                'subtitle': book_info.get('subtitle', ''),
                'authors': book_info.get('authors', []),
                'published_date': book_info.get('publishedDate', ''),
                'description': book_info.get('description', ''),
                'publisher': book_info.get('publisher', ''),
                'page_count': book_info.get('pageCount', 0),
                'cover_url': None,
            }
            # Get cover image URL
            if 'imageLinks' in book_info and 'thumbnail' in book_info['imageLinks']:
                standardized_data['cover_url'] = book_info['imageLinks']['thumbnail']
            else:
                standardized_data['cover_url'] = None
            return standardized_data
        else:
            logging.info("Book not found in Google Books API, trying OpenLibrary API")
    except requests.exceptions.RequestException as e:
        logging.error(f"Error accessing Google Books API: {e}")
        send_push(f"Error attempting to find book {isbn} in Google Books API", str(e))

    # Try OpenLibrary API
    base_url_openlibrary = f"https://openlibrary.org/api/books?bibkeys=ISBN:{isbn}&jscmd=details&format=json"
    try:
        response = requests.get(base_url_openlibrary)
        response.raise_for_status()
        book_data = response.json()
        if f"ISBN:{isbn}" in book_data:
            book_info = book_data[f"ISBN:{isbn}"]
            details = book_info.get("details", {})
            logging.info(f"Found {details.get('title', 'Unknown Title')} using OpenLibrary API")
            # Standardize the data
            standardized_data = {
                'title': details.get('title', ''),
                'subtitle': details.get('subtitle', ''),
                'authors': [],
                'published_date': details.get('publish_date', ''),
                'description': '',
                'publisher': ', '.join(details.get('publishers', [])) if 'publishers' in details else '',
                'page_count': details.get('number_of_pages', 0),
                'cover_url': None,
            }
            # Authors
            if 'authors' in details:
                standardized_data['authors'] = [author.get('name', 'Unknown') for author in details['authors']]
            else:
                standardized_data['authors'] = []

            # Description
            if 'description' in details:
                if isinstance(details['description'], dict):
                    standardized_data['description'] = details['description'].get('value', '')
                elif isinstance(details['description'], str):
                    standardized_data['description'] = details['description']
            else:
                standardized_data['description'] = ''

            # Cover URL
            if 'covers' in details and details['covers']:
                cover_id = details['covers'][0]
                standardized_data['cover_url'] = f"https://covers.openlibrary.org/b/id/{cover_id}-L.jpg"
            elif 'thumbnail_url' in book_info:
                standardized_data['cover_url'] = book_info['thumbnail_url'].replace('-S.jpg', '-L.jpg')
            else:
                standardized_data['cover_url'] = None

            return standardized_data
        else:
            logging.info("Book not found in OpenLibrary API")
            logging.warning(
                "No data found for the following ISBN %s. Check and see if it is correct",
                isbn,
            )
            send_push(
                f"No data found for ISBN: {isbn}",
                f"Check for another ISBN. No data was found for ISBN: {isbn}",
            )
            return None
    except requests.exceptions.RequestException as e:
        logging.error(f"Error accessing OpenLibrary API: {e}")
        send_push(f"Error attempting to find book {isbn} in OpenLibrary API", str(e))
        return None


def get_pages(num_pages=None):
    url = f"https://api.notion.com/v1/databases/{DATABASE_ID}/query"
    # payload = {"page_size": 100 if num_pages is None else num_pages}
    payload = {
        "filter": {"property": "Name", "title": {"contains": "New Book"}},
        "page_size": 100 if num_pages is None else num_pages,
    }
    logging.info("Looking for New Books...")
    results = []

    with requests.post(url, json=payload, headers=NOTION_HEADERS) as response:
        data = response.json()
        results.extend(data["results"])

        while data.get("has_more") and num_pages is None:
            payload["start_cursor"] = data["next_cursor"]
            with requests.post(url, json=payload, headers=NOTION_HEADERS) as response:
                data = response.json()
                results.extend(data["results"])

    return results


def read_pages():
    pages = get_pages()

    for count, page in enumerate(pages, start=1):
        try:
            page_id = page["id"]
            props = page["properties"]

            # Safely retrieve ISBN
            isbn_field = props.get("ISBN", {}).get("rich_text", [])
            if isbn_field:
                isbn = isbn_field[0].get("plain_text", "")
            else:
                logging.error(f"No ISBN found for page {page_id}. Skipping...")
                continue  # or handle accordingly

            title_field = props.get("Name", {}).get("title", [])
            if title_field:
                title = title_field[0].get("plain_text", "")
            else:
                logging.error(f"No title found for page {page_id}. Skipping...")
                continue

            if "New Book" in title and isbn:
                logging.info("Found a new book")
                book_data = get_book(isbn)

                if book_data:
                    update_notion(book_data, page_id, isbn)
        except (KeyError, IndexError) as e:
            logging.error(f"Error reading page {count}: {e}")
            send_push("Error reading Notion book page", f"Page {count}: {e}")


def update_page(page_id, data):
    url = f"https://api.notion.com/v1/pages/{page_id}"

    res = requests.patch(url, json=data, headers=NOTION_HEADERS)

    if res.status_code == 200:
        logging.info("Book details updated successfully!")
    else:
        logging.error(
            f"Notion update request failed with status code: {res.status_code}"
        )
        json_data = res.json()
        for key, value in json_data.items():
            logging.error(f"{key}: {value}")
        send_push(
            f"Error {json_data['status']}: {json_data['code']}", json_data["message"]
        )


def make_banner(img_url, page_id):
    img_name = f"{page_id}.jpg"
    urllib.request.urlretrieve(img_url, img_name)

    img = Image.open(img_name).convert("RGB")
    new_height = 540
    new_width = int(new_height * img.width / img.height)
    img_poster = img.resize((new_width, new_height))
    upload_file(img_name, img_name, "book_covers/")

    cropped_img = (
        img.crop((5, img.height // 3, img.width, 2 * img.height // 3))
        .resize((1500, 600))
        .filter(ImageFilter.BoxBlur(30))
    )
    cropped_img.paste(img_poster, (573, 30))
    cropped_img.save(img_name)

    upload_file(img_name, img_name, "book_banners/")

    return cropped_img


def get_book_cover_from_isbndb(isbn):
    # Send a request to the ISBNdb book page
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"}
    book_url = (f"https://isbndb.com/book/{isbn}")
    response = requests.get(book_url, headers=headers)

    # Parse the page content
    soup = BeautifulSoup(response.content, 'html.parser')

    # Find the div with the class "artwork" and then locate the object tag inside it
    artwork_div = soup.find("div", {"class": "artwork"})

    if artwork_div:
        # Find the object tag within the div and get the data attribute
        object_tag = artwork_div.find("object")
        if object_tag and "data" in object_tag.attrs:
            image_url = object_tag['data']
            logging.info(f"Cover image URL: {image_url}")
            return image_url
        else:
            logging.info("Object tag or 'data' attribute not found.")
    else:
        logging.info("Div with class 'artwork' not found.")


def get_book_cover_from_openlibrary(isbn):
    url = (
        f"https://openlibrary.org/api/books?bibkeys=ISBN:{isbn}&jscmd=data&format=json"
    )

    response = requests.get(url)

    if response.status_code == 200:
        book_info = response.json().get(f"ISBN:{isbn}", {})
        openlibrary_ids = book_info.get("identifiers", {}).get("openlibrary", [])

        if openlibrary_ids:
            return f"https://covers.openlibrary.org/b/olid/{openlibrary_ids[0]}-L.jpg"
        else:
            logging.info("No openlibrary ID found.")
    else:
        logging.info(f"Failed to retrieve data. Status code: {response.status_code}")


def update_notion(book_data, page_id, isbn):
    title = book_data.get("title", "")

    if "subtitle" in book_data:
        title += f": {book_data['subtitle']}"
    title = re.sub(r"\([^)]*\)", "", title)[:100]

    cover = book_data.get('cover_url') or get_book_cover_from_openlibrary(isbn) or get_book_cover_from_isbndb(isbn) or "https://upload.wikimedia.org/wikipedia/commons/c/ca/1x1.png"

    img_name = f"{page_id}.jpg"

    try:
        urllib.request.urlretrieve(cover, img_name)
        img = Image.open(img_name)
    except Exception:
        cover = "https://upload.wikimedia.org/wikipedia/commons/c/ca/1x1.png"
        urllib.request.urlretrieve(cover, img_name)
        img = Image.open(img_name)

    if USE_AWS.lower() == "no":
        cover = cover
        banner = cover
    elif img.size < (50, 50):
        cover = banner = (
            "https://pipedream-api.s3.us-east-2.amazonaws.com/icons/noCover.jpeg"
        )
    else:
        make_banner(cover, page_id)
        banner = (
            f"https://{BUCKET}.s3.{AWS_REGION}.amazonaws.com/book_banners/{page_id}.jpg"
        )
        cover = f"https://{BUCKET}.s3.{AWS_REGION}.amazonaws.com/book_covers/{page_id}.jpg"

    authors = " and ".join(book_data.get("authors", ["Anthology"]))
    published_date = book_data.get("publishedDate", "")
    description = remove_html(book_data.get("description", ""))
    description = textwrap.shorten(
        description.replace('"', "").replace("\n", ""), width=2000, placeholder="..."
    )
    publisher = (
        book_data.get("publisher", "No Publisher Found")
        .replace(",", "")
        .replace(";", "")
    )
    year = parser.parse(published_date).year if published_date else None
    page_count = book_data.get("pageCount", 0)

    update_data = {
        # Notion only accepts cover URLs over HTTPS
        "cover": {"external": {"url": banner.replace("http://", "https://")}},
        "properties": {
            "Author": {"select": {"name": authors}},
            "Publisher": {"select": {"name": publisher}},
            "ISBN": {"rich_text": [{"text": {"content": isbn}}]},
            "Summary": {"rich_text": [{"text": {"content": description}}]},
            "Type": {"select": {"name": "Physical"}},
            "Cover": {"files": [{"name": title, "external": {"url": cover}}]},
            "Year": {"number": year},
            "Pages": {"number": page_count},
            "Name": {"title": [{"text": {"content": title}}]},
        },
    }

    update_page(page_id, update_data)
    send_push("New book found!!!", f"Adding {title} to your book collection")
    os.remove(img_name)


read_pages()
schedule.every(60).seconds.do(read_pages)
logging.info("Next scan scheduled...")

while True:
    schedule.run_pending()
    time.sleep(1)
