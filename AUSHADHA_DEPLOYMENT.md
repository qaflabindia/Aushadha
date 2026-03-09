# Aushadha Deployment Guide

This document outlines the steps to deploy the **Aushadha** platform locally or on a server using Docker Compose. The platform consists of a Neo4j database, a Python FastAPI backend, a Node/Vite frontend React application, a PostgreSQL database, and local LLM services.

## Prerequisites

Ensure you have the following installed on your host machine:
- **Docker** (version 20.10 or higher)
- **Docker Compose** (V2 recommended)
- **Git** (to clone the repository)
- **Node.js 20+** & **Yarn** (optional, for local frontend development only)
- **Python 3.11+** (optional, for local backend development only)

---

## 1. Clone the Repository
Clone the project repository to your local machine:
```bash
git clone <repository_url>
cd Aushadha
```

---

## 2. Environment Configuration

You must set up environment variables for both the backend and frontend. The `docker-compose.yml` expects these files to be present at `./backend/.env` and `./frontend/.env`.

### Backend Configuration (`backend/.env`)
Create a `.env` file in the `backend/` directory:
```bash
# database configurations
NEO4J_URI=bolt://neo4j:7687
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=<your_secure_neo4j_password>
NEO4J_DATABASE=neo4j

POSTGRES_USER=aushadha_user
POSTGRES_PASSWORD=<your_secure_postgres_password>
POSTGRES_DB=aushadha

# APIs and LLMs
OPENAI_API_KEY=<your_openai_api_key>
DIFFBOT_API_KEY=<your_diffbot_api_key>

# LLM model configs (adjust based on what models you run)
LLM_MODEL_CONFIG_ollama_llama3=llama3,http://local-llm-proxy:8090/v1
```

### Frontend Configuration (`frontend/.env`)
Create a `.env` file in the `frontend/` directory:
```bash
VITE_BACKEND_API_URL=http://localhost:8000
VITE_REACT_APP_SOURCES=local,youtube,wiki,s3,web
VITE_CHAT_MODES=vector,graph,graph_vector
VITE_ENV=DEV
```

---

## 3. Deployment with Docker Compose

Aushadha's services are fully containerized. You can bring up the entire stack using Docker Compose. 

### Starting the Stack
From the root of the `Aushadha` project directory, run:
```bash
docker compose up -d --build
```

This will build the images and launch the following services in detached mode:
1. **neo4j**: The graph database (Ports: `7474`, `7687`).
2. **postgres**: The relational database (Port: `5432`).
3. **backend**: The FastAPI application serving the API (Port: `8000`).
4. **frontend**: The Vite React frontend (Port: `8080`).
5. **local-llm**: The local LLM engine.
6. **local-llm-proxy**: A FastAPI proxy in front of the local LLM.

### Verifying the Setup
1. **Frontend App**: Open your browser and navigate to `http://localhost:8080`
2. **Backend API Docs**: Navigate to `http://localhost:8000/docs` to view the Swagger API documentation.
3. **Neo4j Browser**: Navigate to `http://localhost:7474` (Login: `neo4j` / `<your_secure_neo4j_password>`).

### Viewing Logs
To view logs for all services and follow them in real-time, run:
```bash
docker compose logs -f
```
To view logs for a specific service (e.g., backend):
```bash
docker compose logs -f backend
```

### Stopping the Stack
To stop the services without deleting the data volumes:
```bash
docker compose stop
```
To bring down the services and remove the containers and networks:
```bash
docker compose down
```
**Note:** If you also want to delete the persistent data (Neo4j and Postgres volumes), run `docker-compose down -v`.

---

## 4. Alternate Option: Local Development (Without Docker Compose)
If you prefer running the backend and frontend natively for development:

### Run Neo4j and Postgres locally
You can use docker solely to spin up databases:
```bash
docker compose up -d neo4j postgres
```

### Run the Backend Locally
```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn score:app --reload --host 0.0.0.0 --port 8000
```
*(Ensure `backend/.env` has `NEO4J_URI=bolt://localhost:7687` instead of `neo4j` as the host).*

### Run the Frontend Locally
```bash
cd frontend
yarn install
yarn run dev
```

The frontend will be available at `http://localhost:5173`.

---

## 5. Troubleshooting
- **Frontend fails to start or shows module not found**: Make sure `yarn install` completed successfully. Sometimes clearing `node_modules` and rebuilding the container helps: `docker compose build --no-cache frontend`
- **Neo4j connection refused**: The DB might take up to a minute to allocate its heap memory. Wait briefly and check the Neo4j logs: `docker compose logs -f neo4j`
- `host.docker.internal` **issues on Linux**: If you're on a Linux host, ensure your docker setup supports the `EXTRA_HOSTS` configuration in the compose file.
