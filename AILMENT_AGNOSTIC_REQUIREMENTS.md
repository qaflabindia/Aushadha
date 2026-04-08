# Functional and Technical Requirements Specifications
## Project: YogNayur (Ailment Agnostic Proof of Concept)

### 1. Problem Statement and Scope
The goal is to use AI to improve structured Electronic Health Records (EHR) creation, support early warning signals for localized disease surges, and enable personalized, evidence-informed AYUSH-aligned treatment and lifestyle recommendations with explainability and clinical trust.

**Stage 1 Scope:**
- **Use Case 1:** Multilingual clinician note to structured EHR (Hindi/English).
- **Use Case 2:** Personalized AYUSH-aligned care planning with a Clinician Trust Layer.
- **Use Case 3:** Early warning signals from aggregated synthetic counts.

### 2. Ailment-Agnostic Data Model
Instead of hardcoded fields for a specific condition (e.g., Blood Pressure for Hypertension), the system shall support a dynamic extraction schema.

#### 2.1 Core EHR Schema (Generic)
| Field | Type | Required | Description |
| :--- | :--- | :--- | :--- |
| `case_id` | string | Yes | Unique system-generated ID. |
| `visit_date` | date | Yes | YYYY-MM-DD. |
| `condition_name` | string | Yes | The primary ailment or condition being tracked. |
| `chief_complaint`| string | Yes | Primary reason for visit. |
| `vitals` | object | Optional | Key-value pairs of relevant metrics (e.g., Temp, BP, HR). |
| `symptoms` | list | Optional | List of symptoms with Tri-State status (True, False, Unknown). |
| `lifestyle_factors`| list | Optional | Relevant factors (Diet, Sleep, Stress). |
| `red_flag_any` | bool | Yes | Computed flag for high-risk cases. |
| `clinician_review_status` | enum | Yes | Draft, Edited, Confirmed. |

#### 2.2 Dynamic Red Flag Logic
Red flags are triggered based on:
1.  **Metric Thresholds**: Defined per `condition_name`.
2.  **Critical Symptoms**: Presence of predefined high-risk symptoms.
3.  **Comorbidities**: High-risk combinations.

### 3. Functional Requirements
- **Extraction (UC1):** The system shall use LLMs to map unstructured clinical notes into the generic schema based on the detected `condition_name`.
- **Care Planning (UC2):** AI generates recommendations structured by:
    - `DIET`, `ACTIVITY`, `SLEEP`, `STRESS`, `YOGA`, `FOLLOWUP`, `REFERRAL`.
- **Trust Layer:** Every recommendation must show:
    - Evidence basis, Confidence level, Safety status.
- **Early Warning (UC3):** Monitor trends in `condition_name` surges across localities.

### 4. Technical Guardrails
- **No Cure Claims**: System must not claim to cure any condition.
- **No Dosing**: Herb/medicine dosing is prohibited in AI outputs.
- **Safety Gate**: Any high-risk trigger must force a "Referral First" output style.
