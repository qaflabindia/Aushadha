import asyncio
import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from functools import partial
from typing import Any, Callable

from langchain_core.messages import AIMessage, BaseMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableLambda, RunnableParallel

from src.shared.constants import CHAT_AYUSH_MODE, AYUSH_MASTER_PROMPT


AYUSH_SHARED_SYSTEM_PROMPT = """You are the AYUSH Clinical Intelligence sidecar for a medical intelligence system.

You must stay consistent across all staged calls in this session.

Global rules:
- Use the same target disease and patient context throughout the session.
- Prefer patient KG context and supplied evidence over generic assumptions.
- Do not invent missing facts, citations, doses, outcomes, ADRs, PMCID, DOI, or CTRI identifiers.
- If evidence is missing, write LEC explicitly.
- Treat the triage gate as a safety section inside the report, not as a reason to stop generating the remaining report.
- Keep section outputs clean and scoped only to the requested section.
- Do not repeat full document titles or duplicate headings unless the section explicitly requires them.
- The AYUSH master prompt is the governing contract. Follow its source order, extraction requirements, and output rules unless a step-specific instruction narrows the output to one section.
"""


TRIAGE_GATE_TEMPLATE = """You are Step 0 of an AYUSH clinical intelligence pipeline.
Decide whether AYUSH report generation may proceed for the target condition.

Return markdown for this exact section heading only:
## 1. TRIAGE GATE — MANDATORY FIRST CHECK

Then use exactly this field structure:
VERDICT: PASS or FAIL or ESCALATE
EMERGENCY_FLAGS:
- ...
SCOPE_BOUNDARY:
- ...
RATIONALE:
- ...

Rules:
- If any emergency or unmanaged high-risk condition is clearly present, use FAIL.
- If information is insufficient to safely judge, use ESCALATE.
- If no emergency risk is present in context, use PASS.
- Keep this short and clinical.

Target condition: {disease_name}
ICD code: {icd_code}
Patient profile:
{patient_profile}

Recent chat context:
{recent_history}
"""


DISEASE_MAP_TEMPLATE = """You are Step 1 of an AYUSH clinical intelligence pipeline.
Build Section 2: Disease Entity Mapping for the target condition.

Use only the provided context and well-established clinical terminology. If a subfield is unsupported, write LEC.
Return markdown with this exact heading:
## 2. DISEASE ENTITY MAPPING

Include:
- Biomedical term + ICD code
- Ayurveda term + Unani term + Siddha term
- Dosha classification + Kriyakala stage
- NLP symptom entities table with exact columns:
  | AYUSH Term | Biomedical Equivalent | Prevalence % | Evidence/Source |

Target condition: {disease_name}
ICD code: {icd_code}
Context:
{context}
"""


PHARMACOLOGY_TEMPLATE = """You are Step 3 of an AYUSH clinical intelligence pipeline.
Build Section 3 only.

Return markdown with this exact heading:
## 3. PHARMACOLOGICAL INTERVENTIONS

Requirements:
- One subsection per intervention
- For each intervention, render:
  1. an ATTRIBUTE / DETAIL table
  2. an OUTCOMES table with exact columns:
     | Study | Design / n | Dose / Duration | Outcome | Significance | Source |
  3. an ADR FLAGS block
- Exact dose and exact outcome wherever supported
- Include study design, sample size, source, evidence grade, and ADR flags
- If evidence is missing, write LEC explicitly

Target condition: {disease_name}
Evidence bundle:
{evidence_bundle}

Memory context:
{memory_context}
"""


FORMULATIONS_AND_PROCEDURES_TEMPLATE = """You are Steps 4 and 5 of an AYUSH clinical intelligence pipeline.
Build both sections below and nothing else.

Return markdown with these exact headings:
## 4. COMPOSITE FORMULATIONS
## 5. PANCHAKARMA / PROCEDURAL THERAPIES

Requirements:
- Section 4 must use a table with exact columns:
  | Formulation | Constituents | Evidence Base | Outcome Summary | Source | Notes |
- Section 5 must use a table with exact columns:
  | Procedure | Oils/Materials | Mechanism | Clinical Use Context | Quantified Outcome | Contraindications | Evidence Grade | Source |
- If unsupported, write LEC explicitly

Target condition: {disease_name}
Evidence bundle:
{evidence_bundle}
"""


YOGA_TEMPLATE = """You are Step 6 of an AYUSH clinical intelligence pipeline.
Build Section 6 only.

Return markdown with this exact heading:
## 6. YOGA / PRANAYAMA PROTOCOL

Requirements:
- Named techniques only
- Duration and frequency
- Quantified outcomes where available
- Source/project reference
- Render as a table with exact columns:
  | Technique | Duration | Frequency | Quantified Outcome | Source / Project | Evidence Grade |
- If unsupported, write LEC explicitly

Target condition: {disease_name}
Evidence bundle:
{evidence_bundle}
"""


PHARMACOVIGILANCE_TEMPLATE = """You are Step 7 of an AYUSH clinical intelligence pipeline.
Build Section 7 only using the pharmacological section and evidence bundle.

Return markdown with this exact heading:
## 7. PHARMACOVIGILANCE

Requirements:
- Named ADRs
- Drug interactions
- Contraindicated conditions
- Render as a table with exact columns:
  | Drug / Herb | Known ADRs | Interaction Flags | Contraindicated Conditions | Source |
- If unsupported, write LEC explicitly

Target condition: {disease_name}
Pharmacology section:
{pharmacology_section}

Evidence bundle:
{evidence_bundle}
"""


ROUTING_TEMPLATE = """You are Step 8 of an AYUSH clinical intelligence pipeline.
Build Section 8 only.

Return markdown with this exact heading:
## 8. ENTITY-TO-INTERVENTION ROUTING TABLE

Requirements:
- Route extracted clinical entity clusters to first-line AYUSH interventions and doses
- If a severe interaction/contraindication is present, mark the row with WARNING
- Render as a table with exact columns:
  | Extracted Entity Cluster | First-line AYUSH Intervention | Dose | Evidence Grade | Safety Flag |
- If unsupported, write LEC explicitly

Target condition: {disease_name}
Disease map:
{disease_map}

Pharmacology:
{pharmacology_section}

Formulations and procedures:
{formulations_section}

Yoga:
{yoga_section}

Pharmacovigilance:
{pharmacovigilance_section}
"""


EVIDENCE_SUMMARY_TEMPLATE = """You are Step 9 of an AYUSH clinical intelligence pipeline.
Build Section 9 only.

Return markdown with this exact heading:
## 9. EVIDENCE GRADE SUMMARY

Requirements:
- Summarize all interventions with grade, study design, sample size, and citation
- Do not invent missing citations
- Render as a table with exact columns:
  | Intervention | Evidence Grade | Study Design | N | Source |
- If unsupported, write LEC explicitly

Target condition: {disease_name}
Pharmacology:
{pharmacology_section}

Formulations and procedures:
{formulations_section}

Yoga:
{yoga_section}

Pharmacovigilance:
{pharmacovigilance_section}

Routing:
{routing_section}
"""


DATA_UNAVAILABLE_MESSAGE = "LEC"

ICD_CODE_LOOKUP = {
    "hypertension": "I10",
    "essential hypertension": "I10",
    "high blood pressure": "I10",
}


RESEARCH_GROUPS = {
    "government": [
        "ayushportal.nic.in",
        "accr.ayush.gov.in",
        "dharaonline.org",
        "echarak.ayush.gov.in",
        "ayushsuraksha.com",
        "ccras.nic.in",
    ],
    "academic": [
        "pubmed.ncbi.nlm.nih.gov",
        "pmc.ncbi.nlm.nih.gov",
        "jaims.in",
        "sciencedirect.com",
    ],
    "meta_analysis": [
        "frontiersin.org",
    ],
}


@dataclass
class AyushSidecarDependencies:
    resolve_chat_model: Callable[[str | None], str]
    get_llm: Callable[..., tuple[Any, str, Any]]
    extract_disease_from_question: Callable[[str, Any], str | None]
    extract_disease_from_history: Callable[[list[BaseMessage], Any], str | None]
    fetch_patient_severity_context: Callable[[Any, str | None], str]
    get_chat_mode_settings: Callable[[str], dict]
    get_neo4j_retriever: Callable[..., Any]
    create_document_retriever_chain: Callable[..., Any]
    retrieve_documents: Callable[..., tuple[list[Any] | None, str | None]]
    conduct_ayush_research: Callable[..., tuple[str, list[str]]]
    get_total_tokens: Callable[[Any, Any], int]
    translate_metadata: Callable[..., Any]


@dataclass
class AyushContextBundle:
    disease_name: str
    icd_code: str
    question: str
    patient_id: str | None
    system_memory: str
    episodic_memory: str
    recent_history: str
    severity_context: str
    patient_graph_context: str
    document_context: str
    document_sources: list[str] = field(default_factory=list)


def _render_message_window(messages: list[BaseMessage], limit: int = 6) -> str:
    if not messages:
        return "LEC"
    rendered: list[str] = []
    for msg in messages[-limit:]:
        role = "assistant" if isinstance(msg, AIMessage) else "user"
        content = getattr(msg, "content", "")
        if isinstance(content, list):
            content = " ".join(str(item) for item in content)
        rendered.append(f"{role.upper()}: {str(content).strip()}")
    return "\n".join(rendered) if rendered else "LEC"


def _render_episodic_memory(messages: list[BaseMessage]) -> str:
    if len(messages) <= 2:
        return "LEC"
    prior_messages = messages[:-2]
    return _render_message_window(prior_messages, limit=min(8, len(prior_messages)))


def _compact_text(text: str, max_chars: int) -> str:
    cleaned = (text or "").strip()
    if not cleaned:
        return ""
    if len(cleaned) <= max_chars:
        return cleaned
    return cleaned[: max_chars - 16].rstrip() + "\n...[truncated]"


def _resolve_icd_code(disease_name: str) -> str:
    lowered = (disease_name or "").strip().lower()
    if not lowered:
        return "N/A"
    if lowered in ICD_CODE_LOOKUP:
        return ICD_CODE_LOOKUP[lowered]
    for alias, code in ICD_CODE_LOOKUP.items():
        if alias in lowered or lowered in alias:
            return code
    return "N/A"


def _invoke_section(
    llm: Any,
    template: str,
    *,
    token_counter: Callable[[Any, Any], int] | None = None,
    **payload: Any,
) -> tuple[str, int]:
    tuned_llm = llm
    try:
        if hasattr(llm, "bind"):
            tuned_llm = llm.bind(temperature=0.1)
    except Exception:
        tuned_llm = llm

    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", AYUSH_SHARED_SYSTEM_PROMPT),
            ("system", "{session_prompt}"),
            ("system", "{master_prompt}"),
            ("system", template),
            ("human", "Complete this section now using the provided inputs only."),
        ]
    )
    response = (prompt | tuned_llm).invoke(payload)
    content = str(getattr(response, "content", "")).strip()
    total_tokens = 0
    if token_counter:
        try:
            total_tokens = token_counter(response, llm)
        except Exception as exc:
            logging.warning("AYUSH sidecar token counting failed: %s", exc)
    return content, total_tokens


def _parse_triage_verdict(content: str) -> str:
    for line in content.splitlines():
        if line.upper().startswith("VERDICT:"):
            verdict = line.split(":", 1)[1].strip().upper()
            if verdict in {"PASS", "FAIL", "ESCALATE"}:
                return verdict
    return "ESCALATE"


def _strip_duplicate_heading(content: str, heading: str) -> str:
    normalized = content.strip()
    if normalized.startswith(heading):
        normalized = normalized[len(heading):].lstrip()
    return normalized


def _run_triage_gate(
    llm: Any,
    context: AyushContextBundle,
    token_counter: Callable[[Any, Any], int] | None = None,
) -> tuple[str, str, int]:
    session_prompt = _build_session_prompt(context)
    content, total_tokens = _invoke_section(
        llm,
        TRIAGE_GATE_TEMPLATE,
        token_counter=token_counter,
        session_prompt=session_prompt,
        master_prompt="",
        disease_name=context.disease_name,
        icd_code=context.icd_code,
        patient_profile=context.patient_graph_context or context.severity_context or "LEC",
        recent_history=context.recent_history,
    )
    return _parse_triage_verdict(content), content, total_tokens


def _fetch_patient_graph_context(graph: Any, patient_id: str | None) -> str:
    if not patient_id:
        return ""

    try:
        query = """
        MATCH (e:__Entity__)
        WHERE e.patient_id = $pid
          AND any(lbl IN labels(e) WHERE lbl IN [
            'Condition', 'Medical Condition', 'MedicalCondition',
            'Symptom', 'Medication', 'Measurement',
            'RiskFactor', 'Risk Factor',
            'Treatment', 'Procedure',
            'Lifestyle', 'Habit'
          ])
        RETURN labels(e) AS labels, e.id AS detail, e.description AS description
        ORDER BY e.id
        """
        rows = graph.query(query, {"pid": patient_id})
        if not rows:
            return ""

        grouped: dict[str, list[str]] = {
            "conditions": [],
            "symptoms": [],
            "medications": [],
            "measurements": [],
            "risk_factors": [],
            "treatments": [],
            "procedures": [],
            "lifestyle": [],
        }

        for row in rows:
            labels = row.get("labels") or []
            detail = row.get("detail") or ""
            desc = row.get("description") or ""
            text = detail.split("_")[-1] if "_" in detail else detail
            if desc:
                text = f"{text} ({desc})"

            if "Medication" in labels:
                grouped["medications"].append(text)
            elif "Measurement" in labels:
                grouped["measurements"].append(text)
            elif "Symptom" in labels:
                grouped["symptoms"].append(text)
            elif "RiskFactor" in labels or "Risk Factor" in labels:
                grouped["risk_factors"].append(text)
            elif "Treatment" in labels:
                grouped["treatments"].append(text)
            elif "Procedure" in labels:
                grouped["procedures"].append(text)
            elif "Lifestyle" in labels or "Habit" in labels:
                grouped["lifestyle"].append(text)
            elif "Condition" in labels or "Medical Condition" in labels or "MedicalCondition" in labels:
                grouped["conditions"].append(text)

        lines = ["### Patient KG Clinical Profile"]
        label_map = {
            "conditions": "Conditions/Comorbidities",
            "symptoms": "Symptoms/Red Flags",
            "medications": "Medications",
            "measurements": "Measurements/Vitals",
            "risk_factors": "Risk Factors",
            "treatments": "Treatments",
            "procedures": "Procedures",
            "lifestyle": "Lifestyle/Habits",
        }
        for key, heading in label_map.items():
            values = list(dict.fromkeys(grouped[key]))
            if values:
                lines.append(f"{heading}:")
                lines.extend(f"- {value}" for value in values)

        return "\n".join(lines)
    except Exception as exc:
        logging.warning("AYUSH sidecar patient graph context fetch failed: %s", exc)
        return ""


def _fetch_document_context(
    deps: AyushSidecarDependencies,
    llm: Any,
    graph: Any,
    document_names: list[str],
    patient_id: str | None,
    messages: list[BaseMessage],
) -> tuple[str, list[str]]:
    doc_context = ""
    doc_sources: list[str] = []
    try:
        vector_fulltext_settings = deps.get_chat_mode_settings(mode="graph_vector_fulltext")
        retriever = deps.get_neo4j_retriever(
            graph=graph,
            document_names=document_names,
            chat_mode_settings=vector_fulltext_settings,
            score_threshold=0.8,
            patient_id=patient_id,
        )
        doc_retriever_chain = deps.create_document_retriever_chain(llm, retriever)
        docs, _ = deps.retrieve_documents(doc_retriever_chain, messages)
        if docs:
            chunks = []
            for doc in docs:
                src = doc.metadata.get("fileName", doc.metadata.get("source", ""))
                if src and src not in doc_sources:
                    doc_sources.append(src)
                chunks.append(doc.page_content)
            doc_context = "\n\n".join(chunks)
    except Exception as exc:
        logging.warning("AYUSH sidecar document retrieval failed (non-fatal): %s", exc)
    return doc_context, doc_sources


def _resolve_disease_name(
    deps: AyushSidecarDependencies,
    llm: Any,
    graph: Any,
    question: str,
    messages: list[BaseMessage],
    patient_id: str | None,
) -> str:
    disease_name = deps.extract_disease_from_question(question, llm) or ""
    if disease_name:
        return disease_name
    if patient_id:
        try:
            res = graph.query(
                "MATCH (e:__Entity__) "
                "WHERE e.patient_id = $pid "
                "AND any(lbl IN labels(e) WHERE lbl IN ['Condition', 'Medical Condition', 'MedicalCondition']) "
                "RETURN e.id AS condition LIMIT 1",
                {"pid": patient_id},
            )
            if res and res[0].get("condition"):
                raw_cond = res[0]["condition"]
                return raw_cond.split("_")[-1] if "_" in raw_cond else raw_cond
        except Exception as exc:
            logging.warning("AYUSH sidecar graph disease lookup failed: %s", exc)
    return deps.extract_disease_from_history(messages, llm) or "Unknown Condition"


def _build_context_bundle(
    deps: AyushSidecarDependencies,
    llm: Any,
    graph: Any,
    question: str,
    document_names: list[str],
    messages: list[BaseMessage],
    patient_id: str | None,
) -> AyushContextBundle:
    disease_name = _resolve_disease_name(deps, llm, graph, question, messages, patient_id)
    severity_context = deps.fetch_patient_severity_context(graph, patient_id)
    patient_graph_context = _fetch_patient_graph_context(graph, patient_id)
    document_context, document_sources = _fetch_document_context(
        deps, llm, graph, document_names, patient_id, messages
    )

    system_memory = (
        "Generate a complete AYUSH clinical intelligence report with no fabrication. "
        "Use LEC only where evidence is missing. Keep the 9-section PDF-style structure intact."
    )
    episodic_memory = _render_episodic_memory(messages)
    recent_history = _render_message_window(messages)

    return AyushContextBundle(
        disease_name=disease_name,
        icd_code=_resolve_icd_code(disease_name),
        question=question,
        patient_id=patient_id,
        system_memory=system_memory,
        episodic_memory=episodic_memory,
        recent_history=recent_history,
        severity_context=severity_context,
        patient_graph_context=patient_graph_context,
        document_context=document_context,
        document_sources=document_sources,
    )


def _retrieve_group(
    deps: AyushSidecarDependencies,
    disease_name: str,
    model: str,
    group_name: str,
    allowed_domains: list[str],
) -> tuple[str, str, list[str]]:
    try:
        text, sources = deps.conduct_ayush_research(
            disease_name,
            model,
            allowed_domains=allowed_domains,
        )
        return group_name, text, sources
    except Exception as exc:
        logging.warning("AYUSH sidecar retrieval group %s failed: %s", group_name, exc)
        return group_name, "", []


def _retrieve_evidence_bundle_sync(
    deps: AyushSidecarDependencies,
    disease_name: str,
    model: str,
) -> tuple[str, list[str]]:
    rendered_groups: list[str] = []
    all_sources: list[str] = []

    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = [
            executor.submit(_retrieve_group, deps, disease_name, model, name, domains)
            for name, domains in RESEARCH_GROUPS.items()
        ]
        for future in as_completed(futures):
            group_name, text, sources = future.result()
            if text:
                rendered_groups.append(f"### {group_name.replace('_', ' ').title()} Findings\n{text}")
            if sources:
                all_sources.extend(sources)

    return "\n\n".join(rendered_groups).strip(), list(dict.fromkeys(all_sources))


async def _retrieve_evidence_bundle(
    deps: AyushSidecarDependencies,
    disease_name: str,
    model: str,
) -> tuple[str, list[str]]:
    return await asyncio.to_thread(_retrieve_evidence_bundle_sync, deps, disease_name, model)


def _safe_section(build_fn: Callable[[], tuple[str, int]]) -> tuple[str, int]:
    try:
        content, tokens = build_fn()
        return (content if content else DATA_UNAVAILABLE_MESSAGE, tokens)
    except Exception as exc:
        logging.warning("AYUSH sidecar section build failed: %s", exc)
        return DATA_UNAVAILABLE_MESSAGE, 0


def _assemble_memory_context(context: AyushContextBundle) -> str:
    return "\n\n".join(
        [
            f"### System Memory\n{context.system_memory}",
            f"### Episodic Memory\n{context.episodic_memory}",
            f"### Recent Context Window\n{context.recent_history}",
            f"### Patient Context\n{context.severity_context or 'LEC'}",
            f"### Patient KG Context\n{context.patient_graph_context or 'LEC'}",
            f"### Supplemental Documents\n{_compact_text(context.document_context or 'LEC', 2200)}",
        ]
    )


def _build_session_prompt(context: AyushContextBundle) -> str:
    return "\n".join(
        [
            "AYUSH session context:",
            f"- Target disease: {context.disease_name}",
            f"- ICD code: {context.icd_code}",
            f"- Patient id: {context.patient_id or 'N/A'}",
            "- Report objective: Produce the full 9-section AYUSH clinical intelligence report.",
            "- Safety objective: Surface triage red flags, but continue the report.",
            "- Context priority: patient KG -> retrieved evidence -> supplemental documents -> recent chat.",
            "- Missing evidence policy: write LEC or DATA UNAVAILABLE, never fabricate.",
            f"- Recent chat summary:\n{context.recent_history}",
            f"- Episodic memory:\n{context.episodic_memory}",
            f"- Patient KG summary:\n{context.patient_graph_context or 'LEC'}",
        ]
    )


def _build_master_prompt(context: AyushContextBundle, normalized_evidence: str) -> str:
    return AYUSH_MASTER_PROMPT.format(
        DISEASE_NAME=context.disease_name,
        ICD_CODE=context.icd_code,
        context="\n\n".join(
            [
                "### Patient KG Clinical Profile",
                context.patient_graph_context or "LEC",
                "### Patient Severity Context",
                context.severity_context or "LEC",
                "### Recent Chat Context",
                context.recent_history or "LEC",
                "### Episodic Memory",
                context.episodic_memory or "LEC",
                "### Supplemental Documents and Retrieved Evidence",
                _compact_text(normalized_evidence or "LEC", 4200),
            ]
        ),
    )


def _should_parallelize_sections(model_name: str) -> bool:
    lowered = (model_name or "").lower()
    return lowered.startswith("gpt-5") or any(lowered.startswith(prefix) for prefix in ("o1", "o3", "o4"))


def _build_section_runnable(
    *,
    llm: Any,
    template: str,
    token_counter: Callable[[Any, Any], int] | None = None,
    session_prompt: str,
    master_prompt: str,
    disease_name: str,
    evidence_bundle: str,
    memory_context: str | None = None,
) -> RunnableLambda:
    payload = {
        "session_prompt": session_prompt,
        "master_prompt": master_prompt,
        "disease_name": disease_name,
        "evidence_bundle": evidence_bundle,
        "memory_context": memory_context or "LEC",
    }
    return RunnableLambda(
        lambda _input: _safe_section(
            lambda: _invoke_section(llm, template, token_counter=token_counter, **payload)
        )
    )


async def _invoke_section_async(runnable: RunnableLambda) -> tuple[str, int]:
    return await asyncio.to_thread(runnable.invoke, {})


async def _run_section_async(build_fn: Callable[[], tuple[str, int]]) -> tuple[str, int]:
    return await asyncio.to_thread(_safe_section, build_fn)


def _record_section(
    sections: dict[str, str],
    totals: list[int],
    name: str,
    result: tuple[str, int],
) -> None:
    content, tokens = result
    sections[name] = content
    totals[0] += tokens


async def run_ayush_sidecar(
    *,
    deps: AyushSidecarDependencies,
    model: str,
    graph: Any,
    document_names: list[str],
    question: str,
    messages: list[BaseMessage],
    history: Any,
    session_id: str,
    language: str = "en",
    patient_id: str | None = None,
) -> dict:
    start_time = time.time()
    model_version = model
    message_window = list(messages)

    try:
        resolved_model = deps.resolve_chat_model(model)
        llm, model_version, _ = deps.get_llm(model=resolved_model)
        context = _build_context_bundle(deps, llm, graph, question, document_names, message_window, patient_id)
        session_prompt = _build_session_prompt(context)
        triage_verdict, triage_section, triage_tokens = _run_triage_gate(
            llm, context, token_counter=deps.get_total_tokens
        )

        sections: dict[str, str] = {"triage": triage_section}
        sources = list(context.document_sources)
        total_tokens = triage_tokens

        evidence_bundle, evidence_sources = await _retrieve_evidence_bundle(
            deps, context.disease_name, resolved_model
        )
        if evidence_sources:
            sources = list(dict.fromkeys(sources + evidence_sources))

        memory_context = _assemble_memory_context(context)
        normalized_evidence = "\n\n".join(
            filter(
                None,
                [
                    f"### Retrieved Evidence Bundle\n{_compact_text(evidence_bundle, 3200)}" if evidence_bundle else "",
                    f"### Supplemental Documents\n{_compact_text(context.document_context, 2200)}" if context.document_context else "",
                    f"### Patient Severity Context\n{_compact_text(context.severity_context, 1200)}" if context.severity_context else "",
                    f"### Patient KG Clinical Profile\n{_compact_text(context.patient_graph_context, 2200)}" if context.patient_graph_context else "",
                ],
            )
        ).strip() or DATA_UNAVAILABLE_MESSAGE
        master_prompt = _build_master_prompt(context, normalized_evidence)

        token_totals = [total_tokens]

        _record_section(
            sections,
            token_totals,
            "disease_map",
            await _run_section_async(
                lambda: _invoke_section(
                llm,
                DISEASE_MAP_TEMPLATE,
                token_counter=deps.get_total_tokens,
                session_prompt=session_prompt,
                master_prompt=master_prompt,
                disease_name=context.disease_name,
                icd_code=context.icd_code,
                context=memory_context + "\n\n" + normalized_evidence,
            )
            ),
        )

        pharmacology_runnable = _build_section_runnable(
            llm=llm,
            template=PHARMACOLOGY_TEMPLATE,
            token_counter=deps.get_total_tokens,
            session_prompt=session_prompt,
            master_prompt=master_prompt,
            disease_name=context.disease_name,
            evidence_bundle=normalized_evidence,
            memory_context=memory_context,
        )
        formulations_runnable = _build_section_runnable(
            llm=llm,
            template=FORMULATIONS_AND_PROCEDURES_TEMPLATE,
            token_counter=deps.get_total_tokens,
            session_prompt=session_prompt,
            master_prompt=master_prompt,
            disease_name=context.disease_name,
            evidence_bundle=normalized_evidence,
        )
        yoga_runnable = _build_section_runnable(
            llm=llm,
            template=YOGA_TEMPLATE,
            token_counter=deps.get_total_tokens,
            session_prompt=session_prompt,
            master_prompt=master_prompt,
            disease_name=context.disease_name,
            evidence_bundle=normalized_evidence,
        )

        if _should_parallelize_sections(model_version):
            parallel_sections = RunnableParallel(
                pharmacology=pharmacology_runnable,
                formulations=formulations_runnable,
                yoga=yoga_runnable,
            )
            section_results = await asyncio.to_thread(parallel_sections.invoke, {})
            _record_section(sections, token_totals, "pharmacology", section_results["pharmacology"])
            _record_section(sections, token_totals, "formulations", section_results["formulations"])
            _record_section(sections, token_totals, "yoga", section_results["yoga"])
        else:
            _record_section(
                sections,
                token_totals,
                "pharmacology",
                await _invoke_section_async(pharmacology_runnable),
            )
            _record_section(
                sections,
                token_totals,
                "formulations",
                await _invoke_section_async(formulations_runnable),
            )
            _record_section(sections, token_totals, "yoga", await _invoke_section_async(yoga_runnable))

        _record_section(
            sections,
            token_totals,
            "pharmacovigilance",
            await _run_section_async(
                lambda: _invoke_section(
                llm,
                PHARMACOVIGILANCE_TEMPLATE,
                token_counter=deps.get_total_tokens,
                session_prompt=session_prompt,
                master_prompt=master_prompt,
                disease_name=context.disease_name,
                pharmacology_section=sections["pharmacology"],
                evidence_bundle=normalized_evidence,
            )
            ),
        )

        _record_section(
            sections,
            token_totals,
            "routing",
            await _run_section_async(
                lambda: _invoke_section(
                llm,
                ROUTING_TEMPLATE,
                token_counter=deps.get_total_tokens,
                session_prompt=session_prompt,
                master_prompt=master_prompt,
                disease_name=context.disease_name,
                disease_map=sections["disease_map"],
                pharmacology_section=sections["pharmacology"],
                formulations_section=sections["formulations"],
                yoga_section=sections["yoga"],
                pharmacovigilance_section=sections["pharmacovigilance"],
            )
            ),
        )

        _record_section(
            sections,
            token_totals,
            "evidence_summary",
            await _run_section_async(
                lambda: _invoke_section(
                llm,
                EVIDENCE_SUMMARY_TEMPLATE,
                token_counter=deps.get_total_tokens,
                session_prompt=session_prompt,
                master_prompt=master_prompt,
                disease_name=context.disease_name,
                pharmacology_section=sections["pharmacology"],
                formulations_section=sections["formulations"],
                yoga_section=sections["yoga"],
                pharmacovigilance_section=sections["pharmacovigilance"],
                routing_section=sections["routing"],
            )
            ),
        )

        triage_notice = ""
        if triage_verdict != "PASS":
            triage_notice = (
                "### Safety Notice\n"
                "Triage identified red flags or incomplete safety data. Continue reading the report as clinical intelligence only; "
                "do not treat this as clearance for standalone AYUSH management.\n"
            )

        triage_body = _strip_duplicate_heading(sections["triage"], "## 1. TRIAGE GATE — MANDATORY FIRST CHECK")

        final_message = "\n\n".join(
            [
                "# AYUSH CLINICAL INTELLIGENCE",
                triage_notice.strip(),
                "## 1. TRIAGE GATE — MANDATORY FIRST CHECK",
                triage_body,
                sections["disease_map"],
                sections["pharmacology"],
                sections["formulations"],
                sections["yoga"],
                sections["pharmacovigilance"],
                sections["routing"],
                sections["evidence_summary"],
            ]
        ).strip()
        if not final_message or final_message == "# AYUSH CLINICAL INTELLIGENCE":
            final_message = (
                "# AYUSH CLINICAL INTELLIGENCE\n\n"
                "LEC\n\n"
                "The AYUSH report could not be fully assembled in this run. "
                "Partial evidence retrieval or model execution failed before section synthesis completed."
            )

        total_tokens = token_totals[0]
        try:
            history.add_user_message(question)
            history.add_ai_message(final_message)
        except Exception as exc:
            logging.error("AYUSH sidecar failed to persist history: %s", exc)

        result_metadata = {
            "sources": sources,
            "model": model_version,
            "nodedetails": {"chunkdetails": [], "entitydetails": [], "communitydetails": []},
            "total_tokens": total_tokens,
            "response_time": round(time.time() - start_time, 2),
            "mode": CHAT_AYUSH_MODE,
            "entities": {"entityids": [], "relationshipids": []},
            "metric_details": {
                "question": question,
                "contexts": (context.document_context or "")[:500],
                "answer": final_message,
            },
            "sections": sections,
            "triage_verdict": _parse_triage_verdict(sections["triage"]),
        }

        if language and language != "en":
            result_metadata = await deps.translate_metadata(result_metadata, language, model)

        return {
            "session_id": session_id or "",
            "message": final_message,
            "info": result_metadata,
            "user": "chatbot",
        }
    except Exception as exc:
        logging.exception("AYUSH sidecar orchestration failed: %s", exc)
        return {
            "session_id": session_id or "",
            "message": "Something went wrong",
            "info": {
                "sources": [],
                "model": model_version,
                "nodedetails": {"chunkdetails": [], "entitydetails": [], "communitydetails": []},
                "total_tokens": 0,
                "response_time": round(time.time() - start_time, 2),
                "mode": CHAT_AYUSH_MODE,
                "entities": {"entityids": [], "relationshipids": []},
                "metric_details": {},
            },
            "user": "chatbot",
        }
