from langchain_neo4j import Neo4jGraph
import logging
import sys

logging.basicConfig(level=logging.INFO)

def test_connection():
    uri = "bolt://neo4j:7687"
    username = "neo4j"
    password = "password"
    database = "neo4j"
    
    print(f"Attempting to connect to {uri} (database: {database}) as {username}...")
    try:
        graph = Neo4jGraph(
            url=uri,
            username=username,
            password=password,
            database=database,
            refresh_schema=False,
            sanitize=True
        )
        result = graph.query("RETURN 'Connection Successful' as message")
        print(f"Success! Query result: {result}")
        
        # Also check vector index status if possible
        dimensions = graph.query("SHOW INDEXES YIELD * WHERE type = 'VECTOR' AND name = 'vector' RETURN options.indexConfig['vector.dimensions'] AS d")
        print(f"Vector index dimensions: {dimensions}")
        
    except Exception as e:
        print(f"FAILED to connect: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    test_connection()
