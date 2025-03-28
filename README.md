# Notion-ISBN

 Python App that Gets ISBN numbers from Notion and populates book data using the Google Books API

 Duplicate the [Notion Books_Template](https://allaboutduncan.notion.site/3db8f153c5734fa883ea28030255a9df?v=c946f182c52d41a0bde3e96a237fb2a4&pvs=4)

 ![Library Example Image](/images/library.png)

This repository helps in managing ISBNs with Notion. Follow the instructions below to clone the repository and install it via Docker CLI or using `docker-compose`.

## Requirements

* [Notion API Key / Custome Integration](https://developers.notion.com/docs/create-a-notion-integration)
* [Google Books API Key](https://developers.google.com/books/docs/v1/getting_started)

## Add-Ons

### Pushbullet
If you'd like to receive notifications when new books are processed or error details pushed to your mobile device, Pushbullet is supported.

In the `docker-compose.yaml` file - configure `USE_PUSHBULLET=yes` and enter your Token in the line provided. 
* [Pushbullet](https://www.pushbullet.com/)

### Pushover
__Removed support for Pushover in v1 release__ May add this back in a future update, but the original library was out of day and not supported in current versions of Python.

### AWS S3 Bucket for Banner Style Page Covers
 ![Example Banner Image](/images/banner.jpg)

If you want the app to generate banner style Notion Page Covers like the image above, you'll need to have an AWS S3 bucket. This will allow the app to upload and store the images in a location where Notion can import them.

In the `docker-compose.yaml` file - configure `USE_AWS=yes` and enter your Access and Secret Keys in the lines provided. 

# Installation

## Clone the Repository

First, you need to clone this repository to your local machine.

```bash
git clone https://github.com/allaboutduncan/notion-isbn.git
cd notion-isbn
```

## Edit the Docker Compose File

For the app to run,  you must edit the `docker-compose.yaml` fle and configure the following environment variables with the appropriate values.

            - USE_AWS=yes/no            
            - AWS_ACCESS_KEY_ID=ENTER-YOUR-ACCESS-KEY-HERE
            - AWS_SECRET_ACCESS_KEY=ENTER-YOUR-SECRET-KEY-HERE
            - AWS_BUCKET=bucket-name
            - NOTION_TOKEN=notion_secret
            - NOTION_DATABASE_ID=notion-database-id
            - GoogleAPIKey=Google-Books-API-Key
            - USE_PUSHBULLET=yes/no
            - PB_TOKEN=pushbullet_access_token

## Installation via Docker Compose (CLI)

Use `docker-compose` to install to load the variables in the yaml file needed to run the app:

1. **Ensure you have Docker Compose installed:**

   Docker Compose is typically included with Docker Desktop on Windows and Mac. On Linux, you may need to install it separately.

2. **Navigate to the project directory:**

   ```bash
   cd notion-isbn
   ```

3. **Run Docker Compose:**

   ```bash
   docker-compose up -d
   ```

   This command will build and start the services defined in the `docker-compose.yaml` file in detached mode.

## Installation via Docker Compose (Portainer)

Copy the following and edit the environment variables

    version: '3.9'
    services:
        notion-books:
            image: allaboutduncan/notion-isbn:latest
            container_name: notion-books
            restart: always
            ports:
                - '3331:3331'
            environment:
                - AWS_ACCESS_KEY_ID=ENTER-YOUR-ACCESS-KEY-HERE
                - AWS_SECRET_ACCESS_KEY=ENTER-YOUR-SECRET-KEY-HERE
                - AWS_BUCKET=bucket-name
                - NOTION_TOKEN=notion_secret
                - NOTION_DATABASE_ID=notion-database-id
                - GoogleAPIKey=Google-Books-API-Key
                - USE_PUSHBULLET=yes/no
                - PB_TOKEN=pushbullet_access_token

## Using the Application

Once the application is running, you should be able to view the logs or in the console see the status, which should read...
'Next scan scheduled...'

The app will check your Notion database every 60 seconds for new books. To create a new book:

1. Duplicate the [Notion Books_Template](https://allaboutduncan.notion.site/3db8f153c5734fa883ea28030255a9df?v=c946f182c52d41a0bde3e96a237fb2a4&pvs=4)
2. Create a new database entry / book
3. Enter "New Book" for the book title
4. Enter the 10-digit or 13-digit ISBN
5. Wait for the data to be popluated (when the process runs every 60-seconds)

## Contributing

If you'd like to contribute to this project, please fork the repository and use a feature branch. Pull requests are warmly welcome.

## Notes

This is my first public project and I've been working/running this personally for 9 months. It's by no means perfect, but I'm interested to get feedback, requests, etc at this point and share it in a more usable way.

If you enjoyed this, want to say thanks or want to encourage updates and enhancements, feel free to [!["Buy Me A Coffee"](https://www.buymeacoffee.com/assets/img/custom_images/orange_img.png)](https://www.buymeacoffee.com/allaboutduncan)


## License

This project is licensed under the GNU General Public License. See the LICENSE file for details.
