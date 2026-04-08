# Task: Investigating Context Retrieval Issue

- [x] Analyze context retrieval logic <!-- id: 0 -->
    - [x] Review `backend/src/QA_integration.py` <!-- id: 1 -->
    - [x] Inspect `backend/src/llm.py` <!-- id: 2 -->
    - [x] Check Neo4j queries <!-- id: 3 -->
- [x] Identify root causes of failures <!-- id: 4 -->
- [x] Fix Ingestion & Data Strategy <!-- id: 6 -->
    - [x] Remove node ID prefixing in `common_fn.py` <!-- id: 11 -->
    - [x] Update queries to be property-based (isolation by `patient_id` property) <!-- id: 12 -->
- [x] Fix AYUSH Report Generation <!-- id: 13 -->
    - [x] Implement history-based disease inference (using LLM) <!-- id: 14 -->
    - [x] Fix broken `:Patient` query in `QA_integration.py` <!-- id: 15 -->
    - [x] Add severity context retrieval (Measurements & Symptoms) <!-- id: 16 -->
- [x] Verify functionality with test scripts <!-- id: 7 -->
- [x] Document final "working" state in walkthrough.md <!-- id: 17 -->
