import requests
from datetime import datetime, timezone
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
from pushover import Pushover
import json
import textwrap

SERVICE_NAME = "Notion Books"
NOTION_TOKEN = os.getenv("NOTION_TOKEN")
DATABASE_ID = os.getenv("NOTION_DATABASE_ID")
NOTION_headers = {
    "Authorization": "Bearer " + NOTION_TOKEN,
    "Content-Type": "application/json",
    "Notion-Version": "2022-06-28",
}
PO_USER = os.getenv("PO_USER")
PO_TOKEN = os.getenv("PO_TOKEN")
po = Pushover(PO_TOKEN)
po.user(PO_USER)

BUCKET = os.getenv("AWS_BUCKET")

GoogleAPIKey = os.getenv("GoogleAPIKey")

def send_push(subject,message):
  msg = po.msg(message)
  msg.set("title", subject)
  po.send(msg)

def status():
    current_time = str(datetime.now())
    subject = SERVICE_NAME + " is online"
    message = SERVICE_NAME + " is online and running at " + current_time
    send_push(subject,message)

def remove_html(input_string):
    soup = BeautifulSoup(input_string, "html.parser")
    return soup.get_text()

def upload_file(file_name,object_name,bucket_folder):
    # If S3 object_name was not specified, use file_name
    if object_name is None:
        object_name = os.path.basename(file_name)
    # Upload the file
    s3_client = boto3.client('s3')
    object_name = bucket_folder+object_name
    #print("Print: "+object_name)
    try:
        response = s3_client.upload_file(file_name, BUCKET, object_name)
        #print(response)
    except ClientError as e:
        logging.error(e)
        #print.error(e)
        return False
    return True

def get_book(isbn):
    isbn = str(isbn)
    base_url = 'https://www.googleapis.com/books/v1/volumes?country=US&q=isbn:'+isbn +'&keyes&key=' + GoogleAPIKey
    #print(base_url)
    try:
        response = requests.get(base_url)
        response.raise_for_status()
        book_data = response.json()
        #print("Getting book data from Google...")
        # print(book_data)
        if book_data['totalItems'] > 0:
          book_data = book_data['items'][0]['volumeInfo']
          print("Found "+book_data['title'])
        else:
            print("Book not found")
            subject = "No data found for ISBN: " + isbn
            message = "Check for another ISBN. No data  was found for ISBN: " + isbn
            send_push(subject,message)
            print("Push Sent")
        return book_data
    except requests.exceptions.RequestException as e:
        print(f"Error: {e}")
        subject = "Error attempting to find book "+book_data['title']
        message = e
        send_push(subject,message)
        return None

def get_pages(num_pages=None):
    #print("Starting to get pages...")
    url = f"https://api.notion.com/v1/databases/{DATABASE_ID}/query"
    #print(url)
    get_all = num_pages is None
    page_size = 100 if get_all else num_pages
    payload = {"page_size": page_size}
    with requests.post(url, json=payload, headers=NOTION_headers) as response:
        data = response.json()
    results = data["results"]
    while data["has_more"] and get_all:
        payload = {"page_size": page_size, "start_cursor": data["next_cursor"]}
        url = f"https://api.notion.com/v1/databases/{DATABASE_ID}/query"
        response = requests.post(url, json=payload, headers=NOTION_headers)
        # print(response.text)
        # print(response.json)
        data = response.json()
        results.extend(data["results"])
    return results

def read_pages():
    #print("Start reading pages from API...")
    pages = get_pages()
    #print("Starting scan for new books...")
    for count, page in enumerate(pages, start=1):
        try:
            page_id = page["id"]
            props = page["properties"]
            isbn = props["ISBN"]["rich_text"][0]["plain_text"]
            title = props["Name"]["title"][0]["plain_text"]
            if "New Physical Book" in title and isbn is not None:
                print("We found a new book")
                #print(f"{count}. {title}, Page ID: {page_id}, ISBN: {isbn}")
                book_data = get_book(isbn)
                update_notion(book_data,page_id,isbn)
        except KeyError as e:
            print(f"Error reading page {count}: {e}")
            subject = "Error reading Notion book page"
            message = count,e,isbn
            send_push(subject,message)

def update_page(page_id: str, data: dict):
    # print("Start Update_Page function")
    url = f"https://api.notion.com/v1/pages/{page_id}"
    payload = data
    res = requests.patch(url, json=payload, headers=NOTION_headers)
    if res.status_code == 200:
        print('Book details updated successfully!')
    else:
        print(f'Notion update request failed with status code: {res.status_code}')

        json_data = json.loads(res.content.decode('utf-8'))
        # Print key-value pairs
        for key, value in json_data.items():
          print(f'{key}: {value}')
          subject = json_data['status'],json_data['code']
          message = json_data['message']
          send_push(subject,message)
    return res

def make_banner(img_url,page_id):
   img_name = str(page_id+".jpg")
   urllib.request.urlretrieve(img_url,img_name) 
   
   img = Image.open(img_name)
   img = img.convert("RGB")
   width, height = img.size

   new_height = 540
   new_width  = new_height * width / height

   postersize = (int(new_width), new_height)
   img_poster = img.resize(postersize)
   bucket_folder = "book_covers/"
   #img_poster.show()
   #add code to upload poster (cover)
   upload_file(img_name,img_name,bucket_folder)

   left = 5
   top = height / 3
   right = width
   bottom = 2 * height / 3
   
   # Cropped image of above dimension
   img = img.crop((left, top, right, bottom))
   newsize = (1500, 600)
   img_banner = img.resize(newsize)
   img_banner = img_banner.filter(ImageFilter.BoxBlur(30))
   #img_banner.show()

   background = img_banner
   foreground = img_poster
   background.paste(foreground, (573,30)) 
   background.save(img_name)
   bucket_folder = "book_banners/"
   upload_file(img_name,img_name,bucket_folder)
   #background.show()
   return background

def get_opencover(isbn):
    # API endpoint
    url = f"https://openlibrary.org/api/books?bibkeys=ISBN:{isbn}&jscmd=data&format=json"

    # Making a GET request to the API
    response = requests.get(url)

    # Checking if the request was successful
    if response.status_code == 200:
        # Parsing the JSON response
        data = response.json()
        # Extracting the 'identifiers.openlibrary' value
        book_info = data.get(f"ISBN:{isbn}", {})
        identifiers = book_info.get("identifiers", {})
        openlibrary_ids = identifiers.get("openlibrary", [])
        # Returning the 'identifiers.openlibrary' value as plain text
        if openlibrary_ids:
            olid = openlibrary_ids[0]
            cover_url = "https://covers.openlibrary.org/b/olid/"+olid+"-L.jpg"
            return cover_url
        else:
            return "No openlibrary ID found."
    else:
        return f"Failed to retrieve data. Status code: {response.status_code}"

def update_notion(book_data,page_id,isbn):
      print("Start Book Update")
      
      try:
          book_data['subtitle']
          title = book_data['title'] + ": " + book_data['subtitle']
          title = re.sub(r'\([^)]*\)', '', title)
          title = title[:100]
      except KeyError:
          title = book_data['title']
          title = re.sub(r'\([^)]*\)', '', title)
      cover = get_opencover(isbn)
      img_name = str(page_id+".jpg")
      try:
          urllib.request.urlretrieve(cover,img_name)
      except Exception as e:
            print(e)
            cover = "https://upload.wikimedia.org/wikipedia/commons/c/ca/1x1.png"
            img_name = str(page_id+".jpg")
            #print(img_name)
            urllib.request.urlretrieve(cover,img_name)
            img = Image.open(img_name)
            pass
      else:
            img = Image.open(img_name)
      width = img.size
      #print(width)
      if width < (50,50):
          print("That image is too small")
          cover = "https://pipedream-api.s3.us-east-2.amazonaws.com/icons/noCover.jpeg"
          banner = "https://pipedream-api.s3.us-east-2.amazonaws.com/icons/noCover.jpeg"
      else:
          make_banner(cover,page_id)
          banner = f"https://{BUCKET}.s3.us-east-2.amazonaws.com/book_banners/"+page_id+".jpg"
          cover = f"https://{BUCKET}.s3.us-east-2.amazonaws.com/book_covers/"+page_id+".jpg"
      publishedDate = book_data['publishedDate']
      try:
          authors = book_data['authors']
          authors = book_data['authors'][0]
      except KeyError:
          authors = "Anthology"
      date_obj = parser.parse(publishedDate)
      year = date_obj.year
      pageCount = book_data['pageCount']
      try:
        description = book_data['description']
        description = remove_html(book_data['description'])
        description = description.replace("\"", "").replace("\n", "")
        description = textwrap.shorten(description, width=2000, placeholder="...")
      except KeyError:
          description = title + " ("+str(year)+") by " + authors
      try:
          publisher = book_data['publisher']
          publisher = publisher.replace(",","").replace(";","")
      except KeyError:
          publisher = "No Publisher Found"
      #print("Build Notion Update")
      update_data = {
      "cover": {
        "external": { "url": banner }
      },
      "properties": {
        "Author": {
          "type": "select",
          "select": { "name": authors }
        },
        "Publisher": {
          "type": "select",
          "select": { "name": publisher }
        },
        "ISBN": {
            "type": "rich_text",
            "rich_text": [
                { "type": "text",
                    "text": { "content": isbn }
                }
            ]
        },  
        "Summary": {
          "type": "rich_text",
          "rich_text": [
            {
              "type": "text",
              "text": { "content": description }
            }
          ]
        },
        "Type": {
          "type": "select",
          "select": { "name": "Physical" }
        },
        "Cover": {
          "type": "files",
          "files": [
            {
              "name": title,
              "type": "external",
              "external": { "url": cover }
            }
          ]
        },
        "Year": { 
          "type": "number",
          "number": year
        },
        "Pages": {
          "type": "number",
          "number": pageCount
        },
        "Name": {
          "type": "title",
          "title": [
            {
              "type": "text",
              "text": {
                "content": title
              }
            }
          ]
        }
      }
  }

      # print("Now Update the page in Notion")
      update_page(page_id,update_data)
      #print(json.dumps(update_data))
      subject = "New book found!!!"
      message = "Adding "+title+" to your book collection"
      send_push(subject,message)
      #print("Remove the temp image")
      img.close()
      os.remove(page_id+".jpg")

# Uncomment to run on app start
# read_pages()
schedule.every(60).seconds.do(read_pages)
print("Next scan scheduled...")

while True:
    schedule.run_pending()
    time.sleep(1)