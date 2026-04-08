
import os
import sys

# Add backend to sys.path
backend_path = os.path.abspath(os.path.join(os.getcwd()))
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

from src.database import SessionLocal
from src.translation_cache import save_to_cache, get_cached_batch
from src.graph_query import process_node

def verify_batch_cache():
    db = SessionLocal()
    try:
        # Save a few test terms
        save_to_cache(db, "Test Term 1", "en", "ta", "தேர்வு 1")
        save_to_cache(db, "Test Term 2", "en", "ta", "தேர்வு 2")
        
        # Batch lookup
        terms = ["Test Term 1", "Test Term 2", "Unknown Term"]
        results = get_cached_batch(db, terms, "en", "ta")
        
        print(f"Batch results: {results}")
        assert results["Test Term 1"] == "தேர்வு 1"
        assert results["Test Term 2"] == "தேர்வு 2"
        assert results["Unknown Term"] is None
        print("Batch cache verification: SUCCESS")
    finally:
        db.close()

def verify_truncation():
    class MockNode:
        def __init__(self, element_id, labels, properties):
            self.element_id = element_id
            self.labels = labels
            self._properties = properties
        def __getitem__(self, key): return self._properties[key]
        def __iter__(self): return iter(self._properties)
        def get(self, key, default=None): return self._properties.get(key, default)

    long_text = "This is a very long description that should be truncated because it exceeds the limit of one hundred characters for the graph visualization label."
    node = MockNode("1", ["Chunk"], {"description": long_text, "name": "Short Name"})
    
    processed = process_node(node)
    desc = processed["properties"]["description"]
    print(f"Truncated description: {desc}")
    assert len(desc) <= 100
    assert desc.endswith("...")
    assert processed["properties"]["name"] == "Short Name"
    print("Property truncation verification: SUCCESS")

if __name__ == "__main__":
    try:
        verify_batch_cache()
        verify_truncation()
    except Exception as e:
        print(f"Verification FAILED: {e}")
        sys.exit(1)
