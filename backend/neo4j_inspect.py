import os
from langchain_neo4j import Neo4jGraph
from dotenv import load_dotenv

load_dotenv()

url = os.getenv("NEO4J_URI", "bolt://localhost:7687")
username = os.getenv("NEO4J_USERNAME", "neo4j")
password = os.getenv("NEO4J_PASSWORD", "password")

graph = Neo4jGraph(url=url, username=username, password=password)

print("--- Document Nodes ---")
docs = graph.query("MATCH (d:Document) RETURN d.fileName as fileName, d.patient_id as patient_id, d.url as url LIMIT 10")
for d in docs:
    print(d)

print("\n--- Chunk Count ---")
counts = graph.query("MATCH (c:Chunk) RETURN count(c) as count")
print(counts)

print("\n--- Index Check ---")
try:
    indexes = graph.query("SHOW INDEXES")
    for idx in indexes:
        print(f"Index: {idx['name']}, State: {idx['state']}, Labels: {idx['labelsOrTypes']}, Props: {idx['properties']}")
except Exception as e:
    print(f"Could not show indexes: {e}")

print("\n--- Sample Hybrid Search Test ---")
# Simulating the retrieval query from constants.py
patient_id = "PT-AP-SANTHO"
test_query = "systolic" # Based on the graph showing Hypertension/BP context
retrieval_query = """
WITH node AS chunk, score
MATCH (chunk)-[:PART_OF]->(d:Document)
WHERE (d.patient_id IS NULL OR d.patient_id = 'PT-AP-SANTHO')
  AND ([] IS NULL OR [] = [] OR d.fileName IN [])
RETURN d.fileName as fileName, count(chunk) as chunks, avg(score) as avg_score
"""

try:
    # We can't easily run vector search from here without embedding models, 
    # but we can check if the MATCH part returns anything if we join manually.
    res = graph.query("MATCH (c:Chunk)-[:PART_OF]->(d:Document) WHERE d.patient_id = 'PT-AP-SANTHO' RETURN d.fileName, count(c)")
    print(f"Chunks for patient {patient_id}: {res}")
    
    res_global = graph.query("MATCH (c:Chunk)-[:PART_OF]->(d:Document) WHERE d.patient_id IS NULL RETURN d.fileName, count(c)")
    print(f"Global Chunks: {res_global}")
except Exception as e:
    print(f"Test query failed: {e}")
