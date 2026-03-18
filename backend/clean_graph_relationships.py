
import os
import sys
import re
import logging
from typing import List

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

try:
    from langchain_neo4j import Neo4jGraph
except ImportError:
    logging.error("langchain_neo4j not found. Make sure it's installed.")
    sys.exit(1)

# Patterns of relationship types that are considered "rubbish"
RUBBISH_PATTERNS = [
    r"(?i)okay,?\s*let\'s\s*tackle",
    r"(?i)tackle\s*this",
    r"(?i)the\s*user\s*wrote",
    r"(?i)here\s*is\s*the\s*translation",
    r"(?i)it\s*means",
    r"(?i)in\s*tamil",
    r"(?i)in\s*hindi",
    r"அடுத்த பகுதி", # Next part
    r"இதன் துணைவகையாக", # As a sub-variant
    r"குறிப்பிடப்பட்டுள்ள", # Mentioned
    r"நிபுணத்துவம்", # Expertise
    r"உருப்படி உள்ளது", # Item exists (Generic filler)
    r"உடன் செயல்படுகிறது", # Works with
    r"உடன் தொடர்புடையது", # Related to
]

def is_rubbish_type(rel_type: str) -> bool:
    """Check if a relationship type is rubbish."""
    if not rel_type:
        return True

    # Check length - unusually long relationship types are often junk
    if len(rel_type) > 50:
        return True
    
    # Check for conversational filler
    for pattern in RUBBISH_PATTERNS:
        if re.search(pattern, rel_type):
            return True
            
    # Check for types containing too many words (likely a sentence)
    words = rel_type.split()
    if len(words) > 5:
        return True
        
    return False

def get_graph():
    """Initialize Neo4jGraph using environment variables."""
    uri = os.environ.get("NEO4J_URI")
    username = os.environ.get("NEO4J_USERNAME")
    password = os.environ.get("NEO4J_PASSWORD")
    database = os.environ.get("NEO4J_DATABASE", "neo4j")
    
    if not all([uri, username, password]):
        logging.error("Neo4j credentials not found in environment variables.")
        sys.exit(1)
        
    return Neo4jGraph(url=uri, username=username, password=password, database=database)

def clean_graph_relationships(dry_run=True):
    try:
        graph = get_graph()
    except Exception as e:
        logging.error(f"Failed to connect to Neo4j: {e}")
        sys.exit(1)
    
    # 1. Get all relationship types
    query_types = "CALL db.relationshipTypes()"
    try:
        result = graph.query(query_types)
        rel_types = [row['relationshipType'] for row in result]
    except Exception as e:
        logging.error(f"Failed to fetch relationship types: {e}")
        return
    
    junk_types = [t for t in rel_types if is_rubbish_type(t)]
    
    if not junk_types:
        logging.info("No junk relationship types found.")
        return

    logging.info(f"Found {len(junk_types)} junk relationship types: {junk_types}")
    
    if dry_run:
        logging.info("DRY RUN: The following relationships would be deleted:")
        for jt in junk_types:
            count_query = f"MATCH ()-[r:`{jt}`]->() RETURN count(r) as count"
            try:
                count_res = graph.query(count_query)
                logging.info(f" - {jt}: {count_res[0]['count']} instances")
            except Exception as e:
                logging.error(f"Error counting {jt}: {e}")
    else:
        logging.info("CLEANING JUNK RELATIONSHIPS...")
        for jt in junk_types:
            delete_query = f"MATCH ()-[r:`{jt}`]->() DELETE r"
            try:
                graph.query(delete_query)
                logging.info(f"Deleted instances of: {jt}")
            except Exception as e:
                logging.error(f"Error deleting {jt}: {e}")
            
    logging.info("Cleanup process completed.")

if __name__ == "__main__":
    # Default to dry run unless --run is passed
    run_cleanup = "--run" in sys.argv
    clean_graph_relationships(dry_run=not run_cleanup)
