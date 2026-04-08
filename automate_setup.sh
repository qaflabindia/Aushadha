#!/bin/bash
set -e

echo "--- Starting Automated Aushadha Setup ---"

# 1. Start Containers
# We use project name 'ayushpragya' as per existing volumes
echo "Starting Docker containers..."
docker compose -p ayushpragya up -d

# 2. Wait for Postgres to be ready
echo "Waiting for Postgres to be ready..."
until docker exec postgres pg_isready -U aushadha_user -d aushadha > /dev/null 2>&1; do
  echo -n "."
  sleep 2
done
echo " Postgres is ready."

# 3. Wait for Neo4j to be ready
echo "Waiting for Neo4j to be ready..."
# Bolt port check or Cypher shell check (password is 'password' by default in .env)
# Using a simple bolt connection test via python in backend if cypher-shell is slow
until docker exec neo4j cypher-shell -u neo4j -p password "RETURN 1" > /dev/null 2>&1; do
  echo -n "."
  sleep 5
done
echo " Neo4j is ready."

# 4. Initialize Database Schema
echo "Creating Postgres tables..."
docker exec backend python3 /code/init_db_tables.py

# 5. Run Seeding Scripts
echo "Seeding default roles..."
docker exec backend python3 /code/seed_roles.py

echo "Seeding default admin user (admin/password)..."
docker exec backend python3 /code/seed_admin.py

echo "Seeding Neo4j medical terminology..."
docker exec backend python3 -m src.seed_medical_terms

echo "Seeding Secret Vault with environment keys..."
# Note: seed_secrets.py uses /code in sys.path
docker exec backend python3 /code/seed_secrets.py

echo "--- Automated Setup Complete! ---"
echo "Application backend: http://localhost:8000"
echo "Application frontend: http://localhost:8080"
echo "Neo4j Browser: http://localhost:7474"
echo "Default Credentials: admin / password"
