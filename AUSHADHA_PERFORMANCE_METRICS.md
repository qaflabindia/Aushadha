# Aushadha Performance Metrics

This document outlines the performance metrics for the Aushadha platform, specifically focusing on Application Loading time, Graph Generation performance, and Chatbot Response times.

These metrics offer a baseline guide for performance expectations and reflect typical times on a multi-service local deployment or a standard cloud server.

| Description | Target |
| :--- | :--- |
| **System Profile** | 4-8 vCPU, 16GB RAM |
| **Database Setup** | Neo4j 5.23+ |
| **LLM Provider** | OpenAI (GPT-4o-mini), Diffbot, Local LLM |

---

## 1. Application Loading Time

These times reflect how quickly the distinct moving parts of the application initialize and become interactive.

| Metric | Target | Actual (Average Baseline) | Details |
| :--- | :--- | :--- | :--- |
| **Frontend: First Contentful Paint (FCP)** | < 1.5s | ~1.2s | Initial rendering of the UI framework over network/localhost. |
| **Frontend: Time to Interactive (TTI)** | < 3.0s | ~2.5s | Time until the user can interact with the app (React/Vite chunk parsing). |
| **Backend: API Cold Start (FastAPI)** | < 2.0s | ~1.5s | Initial startup time of the FastAPI Python server. |
| **Backend: Health Check Endpoint** | < 100ms | ~45ms | Ping response time for routine health probes. |
| **Database: Initialization/Connection** | < 1.0s | ~500ms | Time required to establish connection pools to Neo4j database instances. |

---

## 2. Graph Generation Time

Graph generation requires reading raw documents, chunking the content, extracting nodes and relationships via the LLM API, and persisting them to Neo4j. This process is highly dependent on document size, content density, and the LLM's throughput.

| Source / Size | Extraction Model | Time per Node/Relation Extraction | Total Processing Time (Estimate) | Assumptions & Notes |
| :--- | :--- | :--- | :--- | :--- |
| **PDF Document** (Medium text, 10 pages) | OpenAI GPT-4o-mini | ~4-6 seconds per page/chunk | **~45 - 60 seconds** | Dependent on the API's concurrency rate limits and node depth extraction. |
| **PDF Document** (Medium text, 10 pages) | Diffbot | ~2-3 seconds per page/chunk | **~25 - 30 seconds** | Generally faster due to specialized NLP endpoints for entity extraction. |
| **Webpage** (Standard Article or Wiki) | OpenAI GPT-4o-mini | ~3-5 seconds per chunk | **~15 - 20 seconds** | Scrapes content, processes text, extracts graph representation. |
| **YouTube Video** (10 minute transcription) | OpenAI GPT-4o-mini | ~4-6 seconds per transcript chunk| **~40 - 50 seconds** | Transcript fetching is fast; generating nodes from chunks drives processing time. |
| **Local LLM** (e.g. Llama-3 8B) | Local LLM Engine | ~10-20 seconds per chunk | **~2 - 4 minutes+** | Varies widely based on hardware (e.g., M1/M2 silicon or RTX class GPU). |

> **Note:** Graph generation performance is heavily bottlenecked by chunk size (`VITE_CHUNK_SIZE`), overlap, and external LLM provider latency/rate limits.

---

## 3. Chatbot Response Time

The Chatbot leverages Retrieval-Augmented Generation (RAG). Different chat modes query the Neo4j database differently (pure vector vs hybrid).

| Query Mode | Metric | Target | Actual (Average Baseline) | Details |
| :--- | :--- | :--- | :--- | :--- |
| **Vector Search** (similarity only) | Time to First Token (TTFT) | < 1.0s | **~0.8s** | Nearest-neighbor vector distance search. |
| **Vector Search** | Total Response Time | < 3.0s | **~2.5s** | Total time to retrieve contexts and generate answer text. |
| **Graph + Vector (Hybrid)** | Time to First Token (TTFT) | < 2.0s | **~1.5s** | Combines vector distance with executing Cypher graph queries. |
| **Graph + Vector (Hybrid)** | Total Response Time | < 5.0s | **~3.5s** | Incorporates semantic contexts generated from graph relationships. |
| **Fulltext Search** | Total Response Time | < 2.5s | **~2.0s** | Standard keyword-based DB search using BM25. |
| **Local LLM Query** | Total Response Time | < 10.0s | **~6.0s - 12.0s** | Longer extraction and generation span on consumer hardware. |

---

## 4. Key Performance Optimizations

To improve or maintain target metrics under heavy loads:
*   **LLM API Rate Limiting:** High-volume user requests will trigger 429 Too Many Requests if processing parallel chunks rapidly. Consider implementing an exponential backoff strategy for API limits.
*   **Database Heap Sizing:** Cypher queries navigating graph hierarchies in hybrid mode rely heavily on memory. Ensure the Neo4j config values (like `dbms.memory.heap.max_size`) are tuned according to the node/edge volume.
*   **Chunk Optimizations:** Adjust `VITE_CHUNK_SIZE` and `VITE_TOKENS_PER_CHUNK` to optimize context windows balancing the accuracy vs speed of the extraction model.
