# Task: Fix Neo4j initialization 'params' issue and verify deployment

- [x] Diagnose the 'params' error on the Docker instance
- [x] Implement the fix for the 'params' issue in `QA_integration.py`
- [x] Verify the fix locally/on Docker
- [x] Push the changes to the Docker instances (if applicable) or provide instructions to the user
- [ ] Investigate "Something went wrong" in chat response [x]
- [x] Identify root cause of chat crash (NoneType issue in QA_RAG)
- [x] Implement fix for document_names NoneType handling
- [x] Verify overall conversational flow with simulation script
- [x] Investigate "noSourceFound" in hybrid modes [x]
- [x] Identify root cause (EmbeddingsFilter threshold on aggregated text)
- [x] Implement conditional EmbeddingsFilter in `create_document_retriever_chain`
- [x] Verify fix with simulation script and notify user
- [x] Refresh Docker environment with fresh build
