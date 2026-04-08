# Playbook for a Winning Submission
## Project: YogNayur (Ailment Agnostic)

### 1. Introduction
This playbook provides a standardized approach for delivering a high-quality, AI-enabled AYUSH solution for any medical condition.

### 2. Core Submission Principles
- **Ailment Agnostic Design**: The system must be capable of handling various health conditions by adjusting its extraction schema and knowledge base.
- **Explainability and Trust**: Use the Clinician Trust Layer to provide evidence for every AI-generated recommendation.
- **Safety First**: Implement strict guardrails to prevent prohibited claims (cures, dosing instructions).

### 3. Submission Roadmap
1.  **Requirement Definition**: Use the `AILMENT_AGNOSTIC_REQUIREMENTS.md` as the baseline.
2.  **Dataset Preparation**: Create synthetic case libraries for the target condition(s).
3.  **Model Configuration**: Configure `Aushadha` with the appropriate prompt templates for the target condition.
4.  **Verification**: Execute the performance matrix and evidence pack generation.

### 4. Technical Blueprint
- **Use Case 1 (EHR):** Extract structured data from multilingual clinical notes.
- **Use Case 2 (Care Plan):** Generate personalized recommendations across standardized sections (Diet, Activity, Sleep, Stress, Yoga).
- **Use Case 3 (Early Warning):** Monitor and alert on locality-specific surges.

### 5. Compliance Checklist
- [ ] No "Cure" claims.
- [ ] No herb/medicine dosing.
- [ ] Referral-first logic for high-risk red flags.
- [ ] Full audit logging of clinician and AI actions.
