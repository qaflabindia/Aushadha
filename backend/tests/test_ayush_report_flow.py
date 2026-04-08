import asyncio
from types import SimpleNamespace

from langchain_core.messages import AIMessage, HumanMessage

from src import QA_integration as qa
from src.ayush_sidecar import AyushSidecarDependencies, run_ayush_sidecar


class DummyHistory:
    def __init__(self):
        self.user_messages = []
        self.ai_messages = []

    def add_user_message(self, message):
        self.user_messages.append(message)

    def add_ai_message(self, message):
        self.ai_messages.append(message)

    def clear(self):
        self.user_messages.clear()
        self.ai_messages.clear()

    def add_message(self, message):
        self.ai_messages.append(message)


class PromptStub:
    def __init__(self, sink):
        self.sink = sink

    def __or__(self, llm):
        sink = self.sink

        class Chain:
            def invoke(self, payload):
                sink.append(payload)
                return SimpleNamespace(content="AYUSH REPORT")

        return Chain()


class FakeLLM:
    def __init__(self, responses):
        self.responses = responses


class FakePromptFactory:
    def __init__(self, outputs):
        self.outputs = outputs
        self.calls = []

    def from_messages(self, _messages):
        outputs = self.outputs
        calls = self.calls

        class Prompt:
            def __or__(self, llm):
                class Chain:
                    def invoke(self, payload):
                        calls.append(payload)
                        idx = len(calls) - 1
                        return SimpleNamespace(content=outputs[idx])

                return Chain()

        return Prompt()


def test_conduct_ayush_research_uses_openai_web_search(monkeypatch):
    captured = {}

    class FakeResponse:
        output_text = "Retrieved AYUSH findings"

        def model_dump(self):
            return {
                "output": [
                    {
                        "type": "web_search_call",
                        "action": {
                            "sources": [
                                {"url": "https://ccras.nic.in/example-study"},
                                {"url": "https://pubmed.ncbi.nlm.nih.gov/12345678/"},
                            ]
                        },
                    }
                ]
            }

    class FakeResponses:
        def create(self, **kwargs):
            captured.update(kwargs)
            return FakeResponse()

    class FakeOpenAI:
        def __init__(self, api_key):
            captured["api_key"] = api_key
            self.responses = FakeResponses()

    monkeypatch.setattr(qa, "_resolve_openai_runtime_config", lambda model: ("gpt-5.2", "sk-test"))
    monkeypatch.setattr("openai.OpenAI", FakeOpenAI)

    text, sources = qa.conduct_ayush_research("Hypertension", "openai_gpt_5.2")

    assert text == "Retrieved AYUSH findings"
    assert sources == [
        "https://ccras.nic.in/example-study",
        "https://pubmed.ncbi.nlm.nih.gov/12345678/",
    ]
    assert captured["api_key"] == "sk-test"
    assert captured["model"] == "gpt-5.2"
    assert captured["tool_choice"] == "required"
    assert captured["tools"][0]["type"] == "web_search"
    assert "ccras.nic.in" in captured["tools"][0]["filters"]["allowed_domains"]
    assert "pubmed.ncbi.nlm.nih.gov" in captured["tools"][0]["filters"]["allowed_domains"]


def test_conduct_ayush_research_fails_closed_for_unsupported_provider():
    text, sources = qa.conduct_ayush_research("Hypertension", "gemini_2.5_flash")
    assert text == ""
    assert sources == []


def _build_sidecar_deps(llm):
    async def passthrough_translate_metadata(data, language, model):
        return data

    return AyushSidecarDependencies(
        resolve_chat_model=lambda model: model,
        get_llm=lambda model=None: (llm, "gpt-5.2", None),
        extract_disease_from_question=lambda question, llm: None,
        extract_disease_from_history=lambda messages, llm: "Asthma",
        fetch_patient_severity_context=lambda graph, patient_id: "",
        get_chat_mode_settings=lambda mode: {"mode": "graph_vector_fulltext"},
        get_neo4j_retriever=lambda **kwargs: object(),
        create_document_retriever_chain=lambda llm, retriever, mode=None: object(),
        retrieve_documents=lambda chain, messages: ([], None),
        conduct_ayush_research=lambda disease_name, model, allowed_domains=None: ("", []),
        get_total_tokens=lambda ai_response, llm: 0,
        translate_metadata=passthrough_translate_metadata,
    )


def test_sidecar_prefers_question_then_graph_then_history(monkeypatch):
    prompt_factory = FakePromptFactory(
        [
            "VERDICT: PASS\nRATIONALE:\n- ok",
            "## 2. DISEASE ENTITY MAPPING\nHypertension map",
            "## 3. PHARMACOLOGICAL INTERVENTIONS\nDrugs",
            "## 4. COMPOSITE FORMULATIONS\nForms\n## 5. PANCHAKARMA / PROCEDURAL THERAPIES\nProcedures",
            "## 6. YOGA / PRANAYAMA PROTOCOL\nYoga",
            "## 7. PHARMACOVIGILANCE\nADR",
            "## 8. ENTITY-TO-INTERVENTION ROUTING TABLE\nRouting",
            "## 9. EVIDENCE GRADE SUMMARY\nSummary",
        ]
    )
    monkeypatch.setattr("src.ayush_sidecar.ChatPromptTemplate", prompt_factory)

    captured = []

    deps = _build_sidecar_deps(FakeLLM([]))
    deps.extract_disease_from_question = lambda question, llm: None
    deps.extract_disease_from_history = lambda messages, llm: "Asthma"
    deps.conduct_ayush_research = lambda disease_name, model, allowed_domains=None: (captured.append(disease_name) or "", [])

    graph = SimpleNamespace(query=lambda query, params: [{"condition": "PT-AP-SANTHO_Hypertension"}])

    result = asyncio.run(
        run_ayush_sidecar(
            deps=deps,
            model="openai_gpt_5.2",
            graph=graph,
            document_names=[],
            question="Generate AYUSH clinical research report",
            messages=[HumanMessage(content="Generate AYUSH clinical research report")],
            history=DummyHistory(),
            session_id="s1",
            patient_id="PT-AP-SANTHO",
        )
    )

    assert captured == ["Hypertension", "Hypertension", "Hypertension"]
    assert "Hypertension" in result["message"]
    assert result["info"]["triage_verdict"] == "PASS"


def test_sidecar_returns_data_unavailable_when_research_is_empty(monkeypatch):
    prompt_factory = FakePromptFactory(
        [
            "VERDICT: PASS\nRATIONALE:\n- ok",
            "## 2. DISEASE ENTITY MAPPING\nLEC",
            "",
            "",
            "",
            "",
            "",
            "",
        ]
    )
    monkeypatch.setattr("src.ayush_sidecar.ChatPromptTemplate", prompt_factory)

    deps = _build_sidecar_deps(FakeLLM([]))
    deps.extract_disease_from_question = lambda question, llm: "Hypertension"

    result = asyncio.run(
        run_ayush_sidecar(
            deps=deps,
            model="openai_gpt_5.2",
            graph=SimpleNamespace(query=lambda query, params: []),
            document_names=[],
            question="AYUSH clinical research report for hypertension",
            messages=[HumanMessage(content="AYUSH clinical research report for hypertension")],
            history=DummyHistory(),
            session_id="s2",
            patient_id=None,
        )
    )

    assert "LEC" in result["message"]
    assert result["info"]["sections"]["pharmacology"] == "LEC"
