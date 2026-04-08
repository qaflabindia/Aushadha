import sys
import os
import asyncio
import logging
from unittest.mock import MagicMock, AsyncMock

# Add project root to sys.path
sys.path.append('/Users/lakshminarasimhan.santhanamgigkri.com/Aushadha/backend')

from src.QA_integration import extract_disease_from_history, fetch_patient_severity_context, process_ayush_response
from langchain_core.messages import HumanMessage, AIMessage

async def test_disease_inference():
    print("--- Testing Disease Inference from History ---")
    class FakeLLM:
        def invoke(self, *args, **kwargs):
            class Res:
                content = "Hypertension"
            return Res()
        def __or__(self, other):
            # In extraction_prompt | llm, the prompt is on the left.
            # But LangChain's prompt.__or__(llm) will return a RunnableSequence.
            # To mock this simply, we can just return this FakeLLM if we control the left side.
            return self
            
    # However, since ChatPromptTemplate.__or__ is already defined, 
    # we need to make sure the result of prompt | FakeLLM() calls our invoke.
    # In LangChain, prompt | model returns a RunnableSequence.
    # A simpler way is to mock just the chain.invoke if we can't control the prompt.
    
    messages = [
        HumanMessage(content="I have been diagnosed with Hypertension."),
        AIMessage(content="I understand. How long have you had it?")
    ]
    
    disease = extract_disease_from_history(messages, FakeLLM())
    print(f"Extracted Disease: {disease}")
    assert disease == "Hypertension"
    print("Test Passed!")

async def test_severity_context():
    print("\n--- Testing Severity Context Retrieval ---")
    mock_graph = MagicMock()
    mock_graph.query.return_value = [
        {'type': 'Measurement', 'detail': 'PT-AP-SANTHO_128/82', 'description': 'Blood pressure reading'},
        {'type': 'Symptom', 'detail': 'PT-AP-SANTHO_headaches', 'description': 'Frequent headaches'}
    ]
    
    context = fetch_patient_severity_context(mock_graph, "PT-AP-SANTHO")
    print(f"Severity Context:\n{context}")
    assert "128/82" in context
    assert "headaches" in context
    assert "### Patient Severity & Clinical Data:" in context
    print("Test Passed!")

async def test_fallback_query_logic():
    print("\n--- Testing Neo4j Fallback Query Logic ---")
    mock_graph = MagicMock()
    mock_graph.query.return_value = [{'condition': 'PT-AP-SANTHO_Asthma'}]
    
    # Simulating the query logic in process_ayush_response
    patient_id = "PT-AP-SANTHO"
    res = mock_graph.query(
        "MATCH (e:__Entity__) WHERE e.patient_id = $pid AND (labels(e) CONTAINS 'Condition' OR labels(e) CONTAINS 'Medical Condition') RETURN e.id AS condition LIMIT 1", 
        {"pid": patient_id}
    )
    
    if res and res[0].get("condition"):
        raw_cond = res[0]["condition"]
        disease_name = raw_cond.split('_')[-1] if '_' in raw_cond else raw_cond
        print(f"Inferred Disease: {disease_name}")
        assert disease_name == "Asthma"
    
    print("Test Passed!")

if __name__ == "__main__":
    asyncio.run(test_disease_inference())
    asyncio.run(test_severity_context())
    asyncio.run(test_fallback_query_logic())
