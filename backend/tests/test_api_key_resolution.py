
import os
import sys
from unittest.mock import MagicMock, patch

# Add backend to sys.path
backend_path = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

# Dynamic mocking of missing modules
class MockModule(MagicMock):
    @classmethod
    def __getattr__(cls, name):
        return MagicMock()

def mock_missing_modules():
    modules_to_mock = [
        "langchain_openai", "boto3", "google", "google.auth", "langchain_core",
        "langchain_core.documents", "langchain_google_vertexai", "langchain_groq",
        "langchain_experimental", "langchain_experimental.graph_transformers",
        "langchain_experimental.graph_transformers.diffbot", "langchain_anthropic",
        "langchain_fireworks", "langchain_aws", "langchain_community",
        "langchain_community.chat_models", "langchain_huggingface",
        "langchain_core.callbacks.manager", "langchain_core.messages",
        "langchain_core.prompts", "pydantic", "pydantic.v1", "fastapi", "transformers",
        "neo4j", "neo4j.exceptions", "langchain_neo4j", "langchain_community.graphs",
        "langchain_community.graphs.graph_document", "httpx"
    ]
    for m in modules_to_mock:
        sys.modules[m] = MockModule()

mock_missing_modules()

from src.llm import get_llm

@patch("src.llm.get_value_from_env")
def test_openai_api_key_resolution(mock_get_env):
    def side_effect(key, default=None, data_type=str):
        if key == "LLM_MODEL_CONFIG_OPENAI_GPT_4_5":
            return "gpt-4.5,            OPENAI_API_KEY" # testing with spaces too
        if key == "OPENAI_API_KEY":
            return "actual-secret-key"
        return default

    mock_get_env.side_effect = side_effect
    
    print("Testing get_llm with placeholder resolution...")
    # Import ChatOpenAI to mock it
    import langchain_openai
    
    llm, model_name, _ = get_llm("OPENAI_GPT_4_5")
    
    # Verification
    langchain_openai.ChatOpenAI.assert_called_once()
    call_args = langchain_openai.ChatOpenAI.call_args
    passed_api_key = call_args.kwargs.get("api_key")
    
    print(f"Model Name returned: {model_name}")
    print(f"API Key passed to ChatOpenAI: {passed_api_key}")
    
    assert model_name == "gpt-4.5"
    assert passed_api_key == "actual-secret-key"
    print("SUCCESS: API key placeholder resolved correctly.")

if __name__ == "__main__":
    try:
        test_openai_api_key_resolution()
    except Exception as e:
        print(f"FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
