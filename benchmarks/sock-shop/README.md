# Sock Shop Benchmark Configuration

This folder contains the exact Docker Compose file and OpenAPI specification used in the dissertation experiment.

## How to run
1. Clone the Sock Shop repository alongside this folder.
2. Start the benchmark: `docker-compose -f docker-compose.yml up -d`
3. Verify: `curl http://localhost:80/catalogue`

The API exposes 10 REST operations documented in `sock-shop-oas.json`.
