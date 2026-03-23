
import re
import os
import sys
import logging
import json
import asyncio

# Set up logging to see the info/warning messages
logging.basicConfig(level=logging.INFO)

# Since we are in /code in the container, src is a package
sys.path.append('/code')

from src.QA_integration import QA_RAG

# Mocking graph for tests
class MockGraph:
    def query(self, q, params):
        if "MATCH (p:Patient" in q and params.get("pid") == "PT-AP-SANTHO":
            return [{"condition": "Hypertension"}]
        return []

async def mock_async_ayush(*args, **kwargs):
    return {"mode_triggered": "ayush_clinical"}

async def mock_async_chat(*args, **kwargs):
    return {"mode_triggered": "chat_standard"}

def test_intent_routing():
    print("--- Intent Routing Testing ---")
    questions = [
        ("Generate Ayush clinical research report", "vector"), # Should be overridden
        ("Tell me about Hypertension", "vector"),            # Should NOT be overridden
        ("clinical research on Migraine", "default"),         # Should be overridden
        ("What is Ayurveda?", "vector")                       # Should NOT be overridden (unless 'ayurveda' is a keyword)
    ]
    
    graph = MockGraph()
    # Mocking process_ayush_response to avoid actual LLM calls
    import src.QA_integration
    original_process_ayush = src.QA_integration.process_ayush_response
    original_process_chat = src.QA_integration.process_chat_response
    original_create_history = src.QA_integration.create_neo4j_chat_message_history
    
    src.QA_integration.process_ayush_response = mock_async_ayush
    src.QA_integration.process_chat_response = mock_async_chat
    src.QA_integration.create_neo4j_chat_message_history = lambda *args: type('obj', (object,), {'messages': []})
    
    async def run_tests():
        for q, initial_mode in questions:
            result = await QA_RAG(graph, "mock_model", q, "[]", "test_session", initial_mode, patient_id="PT-AP-SANTHO")
            print(f"Question: '{q}' (Initial Mode: {initial_mode}) -> Triggered: {result.get('mode_triggered')}")
    
    asyncio.run(run_tests())
    
    # Restore
    src.QA_integration.process_ayush_response = original_process_ayush
    src.QA_integration.process_chat_response = original_process_chat
    src.QA_integration.create_neo4j_chat_message_history = original_create_history

if __name__ == "__main__":
    test_intent_routing()
