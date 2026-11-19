import argparse
import asyncio
import os
import sys

from langchain_core.prompts import ChatPromptTemplate

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.QA_integration import conduct_ayush_research, resolve_chat_model
from src.llm import get_llm, translate_text


PDF_MASTER_PROMPT = """You are an AYUSH Clinical Intelligence Research Engine.

Generate a disease-specific AYUSH clinical research report in the exact structured format below, using:
1. provider-native web research results,
2. uploaded document context if present,
3. Neo4j/patient context if present.

You must produce a complete evidence-graded AYUSH clinical intelligence report, not a refusal, not a generic summary,
and not a request for the user to upload more sources if some context already exists.

If specific evidence is unavailable for a section, sub-entity, intervention, dose, outcome, PMCID, DOI, or ADR detail,
mark it as:
LEC = Limited Evidence in Context

Do not fabricate trials, doses, outcomes, PMCID, DOI, CTRI, or citations.

Output structure:
1. TRIAGE GATE
2. DISEASE ENTITY MAPPING
3. PHARMACOLOGICAL INTERVENTIONS
4. COMPOSITE FORMULATIONS
5. PANCHAKARMA / PROCEDURAL THERAPIES
6. YOGA / PRANAYAMA PROTOCOL
7. PHARMACOVIGILANCE
8. ENTITY-TO-INTERVENTION ROUTING TABLE
9. EVIDENCE GRADE SUMMARY

Rules:
- Every claim must be source-attributed.
- Every intervention must include evidence grade.
- State exact dose and exact outcome whenever available.
- If unavailable, write LEC.
- No refusal.
- No fabricated research.
- No wellness/blog filler.
- If live web research returns nothing, still complete the report with LEC markers.

Target condition: {disease_name}
"""


async def main():
    parser = argparse.ArgumentParser(description="Standalone AYUSH clinical report test using PDF-derived master prompt.")
    parser.add_argument("--disease", default="Hypertension")
    parser.add_argument("--model", default="openai_gpt_5.2")
    parser.add_argument("--language", default="en")
    args = parser.parse_args()

    model = resolve_chat_model(args.model)
    llm, model_name, _ = get_llm(model)

    research_text, research_sources = conduct_ayush_research(args.disease, model)

    research_context_parts = [
        f"### AYUSH REPORT OBJECTIVE\n- Target condition: {args.disease}\n- Produce the complete 9-part report.\n- Use only retrieved evidence or mark LEC."
    ]
    if research_text:
        research_context_parts.append(f"### Provider Web Research Findings\n{research_text}")
    else:
        research_context_parts.append(
            "### Provider Web Research Findings\nNo external AYUSH findings were retrieved in this run. Continue with LEC fallback."
        )
    if research_sources:
        research_context_parts.append("### Retrieved Sources\n" + "\n".join(f"- {src}" for src in research_sources))

    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", PDF_MASTER_PROMPT),
            ("human", "Using only the context below, generate the AYUSH clinical intelligence report.\n\n{context}"),
        ]
    )
    chain = prompt | llm
    response = chain.invoke(
        {
            "disease_name": args.disease,
            "context": "\n\n".join(research_context_parts),
        }
    )

    report_text = response.content
    if args.language != "en":
        report_text = await translate_text(report_text, args.language, "en")

    print("---MODEL---")
    print(model_name)
    print("\n---RETRIEVED SOURCES---")
    if research_sources:
        print("\n".join(research_sources))
    else:
        print("LEC")
    print("\n---REPORT---")
    print(report_text)


if __name__ == "__main__":
    asyncio.run(main())
