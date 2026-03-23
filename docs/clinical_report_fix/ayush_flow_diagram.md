# AYUSH Report Generation Flow

This diagram illustrates the enhanced process for generating an AYUSH clinical research report, incorporating conversational history and Neo4j entity data.

```mermaid
graph TD
    A[User Request: 'Generate AYUSH report'] --> B{Disease Name in Query?}
    
    B -- No --> C[Infer Disease from Chat History using LLM]
    B -- Yes --> D[Use Disease from Query]
    
    C --> E{Inferred?}
    D --> F[Check Patient ID]
    
    E -- No --> G[Fallback: Query Neo4j for Patient Conditions]
    E -- Yes --> F
    
    G --> H{Found in Neo4j?}
    H -- No --> I[Ask User for Condition]
    H -- Yes --> F
    
    F --> J[Retrieve Symptoms & Measurements for Patient]
    J --> K[Conduct Live Web Research - PubMed/AYUSH Portals]
    
    K --> L[Assemble Context: History + Docs + Research + Severity]
    L --> M[Invoke LLM with AYUSH Master Prompt]
    M --> N[Output Factual AYUSH Report]
    
    subgraph Severity Context
        J
    end
    
    subgraph History Inference
        C
    end
```

## Key Enhancements
1. **History Inference**: Uses the LLM to understand what disease was discussed previously, even if the current query is generic.
2. **Neo4j Fallback**: Correctly queries for entities prefixed with the `patient_id` (e.g., `PT-AP-SANTHO_hypertension`) instead of looking for a non-existent `Patient` label.
3. **Severity Integration**: Explicitly pulls measurements (e.g., BP `128/82`) and symptoms (e.g., `headaches`) from the graph to provide specific context for the clinical report.
