import asyncio
import logging
import json
from src.shared.localization import translate_graph_labels, translate_metadata

async def test_pure_translation():
    logging.basicConfig(level=logging.INFO)
    
    # Mock data
    nodes = [
        {
            "id": "Node_1",
            "labels": ["Disease"],
            "properties": {
                "id": "Node_1",
                "name": "Hypertension",
                "description": "High blood pressure condition."
            }
        }
    ]
    relationships = [
        {
            "element_id": "Rel_1",
            "type": "TREATS",
            "start_node_element_id": "Node_1",
            "end_node_element_id": "Node_2",
            "properties": {
                "caption": "This drug treats hypertension."
            }
        }
    ]
    
    language = "ta" # Tamil
    model = "anthropic_claude_4.5_sonnet"
    
    print("\n--- Testing Graph Translation ---")
    translated_nodes, translated_rels = await translate_graph_labels(
        list(nodes), list(relationships), language, model
    )
    
    node = translated_nodes[0]
    print(f"Node id (should be English): {node['properties']['id']}")
    print(f"Node name (translated): {node['properties']['name']}")
    print(f"Original properties exists: {'original_properties' in node['properties']}")
    
    rel = translated_rels[0]
    print(f"Rel type (translated/mapped): {rel['type']}")
    print(f"Rel caption (translated): {rel['properties']['caption']}")
    print(f"Original properties exists in Rel: {'original_properties' in rel['properties']}")
    
    # Test rubbish fallback
    print("\n--- Testing Rubbish Fallback ---")
    rubbish_nodes = [
        {
            "id": "Rubbish_Node",
            "properties": {
                "name": "Some Term",
                "description": "This is a prompt to the LLM to output junk." 
            }
        }
    ]
    # We can't easily force the real LLM to output junk here without a specific prompt,
    # but we can verify our "rubbish" detection logic if we mock the LLM response in localization.py.
    # For now, we'll just check if the logic runs.

if __name__ == "__main__":
    asyncio.run(test_pure_translation())
