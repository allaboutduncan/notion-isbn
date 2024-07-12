# notion-isbn
 Python App that Gets ISBN numbers from Notion and populates book data using the Google Books API

 Duplicate the [Notion Books_Template](https://allaboutduncan.notion.site/3db8f153c5734fa883ea28030255a9df?v=c946f182c52d41a0bde3e96a237fb2a4&pvs=4)

 ![Library Example Image](/images/library.png)

# Notion-ISBN

This repository helps in managing ISBNs with Notion. Follow the instructions below to clone the repository and install it via Docker CLI or using `docker-compose`.

## Clone the Repository

First, you need to clone this repository to your local machine.

```bash
git clone https://github.com/allaboutduncan/notion-isbn.git
cd notion-isbn
```

## Edit the Docker Compose File

For the app to run,  you must edit the 'docker-compose.yaml' fle and configure the following environment variables with the appropriate values.

            - AWS_ACCESS_KEY_ID=ENTER-YOUR-ACCESS-KEY-HERE
            - AWS_SECRET_ACCESS_KEY=ENTER-YOUR-SECRET-KEY-HERE
            - AWS_BUCKET=bucket-name
            - NOTION_TOKEN=notion_secret
            - NOTION_DATABASE_ID=notion-database-id
            - GoogleAPIKey=Google-Books-API-Key
            - PO_TOKEN=pushover-app-API-key
            - PO_USER=pushover_user_key

Note: Currently, Pushover is required, but I'll publish an update in the future making it optional. I highly recommend using Pushover, as the app will send you error information if it encouters issues when adding books.

## Installation via Docker CLI

To build and run the Docker container, follow these steps:

1. **Build the Docker Image:**

   ```bash
   docker build -t notion-isbn .
   ```

2. **Run the Docker Container:**

   ```bash
   docker run -d --name notion-isbn notion-isbn
   ```

   This will run the application in a Docker container.

## Installation via Docker Compose

If you prefer to use `docker-compose`, follow these steps:

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

## Accessing the Application

Once the application is running...

## Stopping the Application

To stop the Docker container or services, you can use the following commands:

- **Stopping the Docker Container:**

  ```bash
  docker stop notion-isbn
  ```

- **Stopping the Docker Compose Services:**

  ```bash
  docker-compose down
  ```

## Contributing

If you'd like to contribute to this project, please fork the repository and use a feature branch. Pull requests are warmly welcome.

## License

This project is licensed under the GNU General Public License. See the LICENSE file for details.