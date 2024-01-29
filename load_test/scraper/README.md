# Scraper App

The Scraper App is a lightweight Flask-based web service designed to accept JSON payloads via POST requests to the `/v1/submit` endpoint and save them in JSON files formatted with timestamps. It's Dockerized for easy deployment and isolation.

#### Docker

**Build the Docker image**

```sh
docker build -t scraper .
```


**Run the container**

```sh
docker run -p 8080:8080 -v $(pwd)/requests:/usr/src/app/requests scraper
```

You can now access the service at `http://localhost:8080`.

### Usage

#### Endpoint: `/v1/submit`

- **Method**: POST
- **Content-Type**: application/json
- **Body**: JSON object

**Example**:

```sh
curl -X POST http://localhost:8080/v1/submit -H "Content-Type: application/json" -d '{"key": "value"}'
```

#### File Storage

Submitted JSON payloads are stored in the `requests` directory within the container, with filenames formatted as `payload-YYYY-MM-DD-HH:MM:SS,sss.json`.

#### Usage with MiniMina

If you have minimina network with uptime-service-backend, you can replace it with scraper in order to scrape load to uptime-service-backend.

Change this in docker-compose.yml:
```
   uptime-service-backend-e2e-test:
     container_name: uptime-service-backend-e2e-test
-    image: 673156464838.dkr.ecr.us-west-2.amazonaws.com/block-producers-uptime:2.0.0rc3-e7ad680-testworld-2-0
+    image: scraper
     volumes:
+      - /home/piotr/scraper/requests:/usr/src/app/requests
       - /home/piotr/.minimina/e2e-test:/local-network
       - /home/piotr/.minimina/e2e-test/uptime-storage:/uptime-storage
     environment:
```
and then do:
```
docker compose down
docker compose create
```