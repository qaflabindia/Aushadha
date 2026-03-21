# Fix "noSourceFound" by Disabling Harmful EmbeddingsFilter in Aggregated Modes

The `EmbeddingsFilter` in `create_document_retriever_chain` applies a fixed similarity threshold (default 0.5) to the final text returned by the retriever. While this works for simple `vector` modes (which return short text chunks), it kills results in hybrid/aggregated modes like `graph+vector+fulltext`. In these modes, the retriever returns a large block of text containing chunks, entities, and relationships, which naturally has a lower cosine similarity to a short user question, even when highly relevant.

Since the individual chunks are already filtered at the Neo4j level (using `score_threshold: 0.1`), the second-pass `EmbeddingsFilter` is redundant and harmful for these modes.

## Proposed Changes

### [QA_integration.py](file:///Users/lakshminarasimhan.santhanamgigkri.com/Aushadha/backend/src/QA_integration.py)

#### [MODIFY] [create_document_retriever_chain](file:///Users/lakshminarasimhan.santhanamgigkri.com/Aushadha/backend/src/QA_integration.py)
Update the function to accept `mode` and conditionally apply the `EmbeddingsFilter`.

```python
def create_document_retriever_chain(llm, retriever, mode=None):
    # ...
    # Only apply EmbeddingsFilter for simple vector/fulltext modes.
    # Aggregated modes (graph, entity, global) return complex text that fails fixed thresholding.
    use_filter = mode in [CHAT_VECTOR_MODE, CHAT_FULLTEXT_MODE]
    
    if use_filter:
        embeddings_filter = EmbeddingsFilter(
            embeddings=EMBEDDING_FUNCTION,
            similarity_threshold=CHAT_EMBEDDING_FILTER_SCORE_THRESHOLD
        )
        pipeline_transformers = [splitter, embeddings_filter]
    else:
        pipeline_transformers = [splitter]
        
    pipeline_compressor = DocumentCompressorPipeline(
        transformers=pipeline_transformers
    )
    # ...
```

#### [MODIFY] [setup_chat](file:///Users/lakshminarasimhan.santhanamgigkri.com/Aushadha/backend/src/QA_integration.py)
Pass the current mode to `create_document_retriever_chain`.

```python
    retriever = get_neo4j_retriever(...)
    mode = chat_mode_settings.get("mode")
    doc_retriever = create_document_retriever_chain(llm, retriever, mode=mode)
```

## Verification Plan

### Automated Tests
- **Simulation**: Update `simulate_retriever.py` to use `CHAT_VECTOR_GRAPH_FULLTEXT_MODE` and verify that documents are returned even with the 0.5 threshold logic in place (by verifying the fix).
- **Command**: `docker exec backend python3 /tmp/simulate_retriever.py`

### Manual Verification
- Ask the user to try the chat with `graph+vector+fulltext` mode selected.
- Verify that `sourcesUsed` now shows the relevant documents and "noSourcesFound" is gone.
