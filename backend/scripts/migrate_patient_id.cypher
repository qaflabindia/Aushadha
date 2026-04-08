// ============================================================================
// TIER 2 — Data Migration: remap wrongly-keyed Neo4j nodes
//
// Background: Content.tsx was passing the user's EMAIL as patient_id to
// extractAPI, so Neo4j Document nodes were written with:
//   patient_id = "lakshminarasimhan.santhanam@gigkri.com"
// instead of the correct case_id such as "PT-AP-LAKSHN".
//
// This script corrects existing data ONLY if you choose Path A (in-place fix).
// For a dev/test environment, Path B (re-ingest) is recommended: delete nodes
// below, fix the frontend (already done), re-upload and re-process.
//
// IMPORTANT: Replace OLD_EMAIL and CORRECT_CASE_ID before running.
// OLD_EMAIL    = the email that was incorrectly stored as patient_id
// CORRECT_CASE_ID = the actual case_id from the patients table (e.g. "PT-AP-LAKSHN")
// ============================================================================

// --- PATH A: In-place fix ---
// Step 1: Update Document nodes
MATCH (d:Document)
WHERE d.patient_id = "OLD_EMAIL"
SET d.patient_id = "CORRECT_CASE_ID"
RETURN count(d) AS documents_updated;

// Step 2: Update Chunk nodes (via their linked Documents)
MATCH (d:Document {patient_id: "CORRECT_CASE_ID"})<-[:PART_OF]-(c:Chunk)
WHERE c.patient_id = "OLD_EMAIL"
SET c.patient_id = "CORRECT_CASE_ID"
RETURN count(c) AS chunks_updated;

// Step 3: Verify
MATCH (d:Document)
WHERE d.patient_id = "CORRECT_CASE_ID"
RETURN count(d) AS doc_count, collect(d.fileName)[..5] AS sample_files;

// --- PATH B: Full re-ingest (recommended for dev) ---
// Delete ALL Document + Chunk nodes for the bad patient_id, then re-upload.

// MATCH (d:Document {patient_id: "OLD_EMAIL"})
// OPTIONAL MATCH (d)<-[:PART_OF]-(c:Chunk)
// OPTIONAL MATCH (c)-[:HAS_ENTITY]->(e)
// DETACH DELETE c, d
// RETURN count(d) AS docs_deleted;
//
// After deletion: fix frontend (done), re-upload files, re-extract.
