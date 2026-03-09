# Aushadha: Data Governance and Security Architecture

This document details the data governance, security principles, and access control mechanisms implemented within the Aushadha Clinical Intelligence platform. Given the highly sensitive nature of clinical information (Protected Health Information - PHI) and the multi-tenant architecture of the system, strict boundaries rule the ingestion, retrieval, and inference of knowledge graph data.

---

## 1. Authentication and Identity Management

Aushadha employs a dual-authentication strategy to cater to both institutional (SSO) and localized access requirements.

- **Google OAuth 2.0 Integration:** The platform utilizes Google Sign-In as the primary authentication provider (`@react-oauth/google`). This delegates password security, multi-factor authentication (MFA), and token lifecycles to Google's robust infrastructure.
- **Local JWT Authentication:** For local or programmatic access, the system utilizes JSON Web Tokens (JWT) signed with secure RSA (RS256) algorithms.
- **Token Persistence and Interception:** Authenticated sessions strictly pass Bearer tokens via Axios Interceptors to all backend FastAPI routes, which validates the tokens before granting access to downstream resources.

---

## 2. Role-Based Access Control (RBAC)

Access to data, insights, and administrative functions is strictly governed by user roles.

### Defined Roles

1.  **Patient:** The default role. Patients can only query, converse with, and visualize the Knowledge Graph corresponding to their **own clinical history**. They have zero visibility into other patients' data or system configurations.
2.  **Doctor / Staff:** Clinical personnel handling multiple patients. They operate with elevated privileges but remain constrained to the scope of their assigned or authorized patient roster.
3.  **Admin:** System administrators capable of managing users, configuring LLM parameters, and viewing aggregate statistics. Admins bypass localized data filters _only when permitted by context_ to perform global operations, but do not interact with raw clinical queries by default.

---

## 3. Multi-Tenancy and Logical Data Isolation

Aushadha utilizes **Neo4j Community Edition**, which inherently lacks fine-grained database-level multi-tenancy. To overcome this, Aushadha implements rigorous **Logical Data Separation** built directly into the data access layer.

### The `owner_email` Construct

All unstructured text uploads, document nodes, chunk nodes, and generated entities are permanently tagged with an `owner_email` property upon ingestion.

- **Strict Filtering:** Every Cypher read query (`MATCH`) executed by the backend automatically appends a `WHERE d.owner_email = $owner_email` clause.
- **Enforced Isolation:** If User A queries the LLM graph, the context retriever mathematically cannot access User B's nodes, relationships, or vectors.

### Patient Context Switching (Impersonation Flow)

To allow Doctors and Staff to manage patient data without violating the `owner_email` isolation rule, Aushadha supports explicit **Context Switching**:

1.  **Target User Designation:** Clinical staff select a patient from a secure dropdown populated by an authorized `/rbac/my_patients` endpoint.
2.  **Axios Context Injection:** The frontend injects a `target_user_email` header into API attributes.
3.  **Backend Override:** The Python FastAPI dependency (`Neo4jCredentials`) validates the user's role (Must be `Admin`, `Doctor`, or `Staff`). If authorized, it substitutes the query's `$owner_email` parameter with the `$target_user_email`.
4.  Consequently, the Doctor acts within the perfect contextual sandbox of that specific patient's clinical graph.
5.  **Admin Global View:** When viewing administrative dashboards (where `target_user_email` is intentionally omitted), the strict `owner_email` filter is strategically dropped if and only if `user_role == "Admin"`, providing an aggregate systemic overview without permitting cross-contamination in clinical RAG chats.

---

## 4. Large Language Model (LLM) Governance

When unstructured clinical notes are dispatched to LLMs (either local models like Ollama/Llama-3 or Cloud providers via Langchain) for Knowledge Graph extraction, data privacy is paramount.

- **Stateless Inference:** Extraction pipelines are stateless. LLMs are not trained, fine-tuned, or given permanent memory over the PHI sent to them.
- **Prompt Constraints:** System prompts strictly bind the LLMs to extract information conforming _only_ to the authorized patient schema.
- **Token Usage Auditing:** All queries to premium LLMs (e.g., Gemini, OpenAI) are tracked via token calculators, preventing abuse and ensuring costs are auditable on a per-tenant basis.

---

## 5. File and Object Storage Security

Aushadha's multimodal processing often handles raw physical documents (PDFs, docx).

- **Google Cloud Storage (GCS) / AWS S3:** Raw files can be configured to offload to secure buckets.
- **Ephemeral Processing:** If processed locally, files are stored temporarily in `/merged_dir` and subsequently deleted using `delete_uploaded_local_file` after the chunking and vector embedding process concludes.

---

## 6. Audit and Lifecycle Actions

Data is not just created; it must be securely purged.

- **Cascade Deletions:** When a user requests the deletion of a document via the frontend context menu, the backend `graphDB_dataAccess.py` triggers a cascading Cypher transaction. It securely identifies the document (mandating the `$owner_email` match) and `DETACH DELETE`s the origin document, all overlapping text chunks, generated entities, and hierarchical communities.
- **Exception Handling:** Graph operation anomalies and system failures are persisted to error logs but are sanitized to never leak underlying Neo4j credentials or clinical PHI within stack traces sent to the client.
