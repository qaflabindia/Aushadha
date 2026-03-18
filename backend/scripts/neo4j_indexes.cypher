// ============================================================================
// Neo4j Composite Indexes: patient_id on Document + Chunk
// TIER 7 — Performance hardenening (one-time operation)
// Run via: neo4j-shell, cypher-shell, or the Neo4j Browser
// ============================================================================

// Index on Document.patient_id — speeds every GRAPH_QUERY, sources_list, delete
CREATE INDEX document_patient_id IF NOT EXISTS
FOR (d:Document)
ON (d.patient_id);

// Index on Chunk.patient_id — speeds VECTOR_SEARCH_QUERY, chunk count queries
CREATE INDEX chunk_patient_id IF NOT EXISTS
FOR (c:Chunk)
ON (c.patient_id);

// Verify
SHOW INDEXES WHERE name IN ['document_patient_id', 'chunk_patient_id'];
