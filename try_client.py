
"""Manual check that the real LLMClient works — the productionized version of first_call.py.
 
Run from the repo root (with your venv active):
    python try_client.py
"""
 
from agentic_test_gen.config import load_config
from agentic_test_gen.llm_client import LLMClient
 
config = load_config()
print("Loaded config:", config)
 
client = LLMClient(config)
resp = client.complete(
    system="You are a helpful assistant. Answer in one sentence.",
    user="What is a unit test?",
)
 
print("Reply:", resp.text)
print("Tokens:", resp.total_tokens)