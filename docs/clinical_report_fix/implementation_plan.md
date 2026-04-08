# Implementation Plan - Enhancing Disease Context Retrieval

The AYUSH clinical research report generator currently fails to identify the disease or condition if it was mentioned earlier in the conversation but not in the final "Generate report" request. This plan addresses this by using the LLM to infer the disease name from the conversational history.

## Proposed Changes

### Backend

#### [MODIFY] [QA_integration.py](file:///Users/lakshminarasimhan.santhanamgigkri.com/Aushadha/backend/src/QA_integration.py)

- **Fix Disease Extraction Logic**:
    - Update `process_ayush_response` to check chat history for the disease name if it's not in the current question.
    - Fix the fallback query (line 759) to match the actual graph schema: search for nodes with labels `Condition` or `Medical Condition` that have a `patient_id` property or ID prefix matching the current `patient_id`.
- **Integrate Severity/Measurements**:
    - Add a step to retrieve `Measurement` and `Symptom` entities for the given `patient_id`.
    - Pass these measurements and symptoms as additional context to the `AYUSH_MASTER_PROMPT` to provide the LLM with "severity" and current state information.
- **Robustness**:
    - Use the `llm` to perform a quick "entity resolution" on the history if multiple conditions are mentioned.

## Verification Plan

### Automated Tests
- Create a new test script `/tmp/test_disease_inference.py` that:
    - Mocks the `llm` and `graph` dependencies.
    - Simulates a chat history where a disease (e.g., "Migraine") is discussed.
    - Calls `process_ayush_response` with a follow-up query "Generate AYUSH clinical research report".
    - Verifies that "Migraine" is correctly identified as the `disease_name`.

### Manual Verification
- Request the user to test the following flow in the UI:
    1. Ask: "I have been suffering from Asthma for 2 years."
    2. Ask: "Generate AYUSH clinical research report."
    3. Verify that the assistant generates a report for Asthma instead of asking for the condition.
