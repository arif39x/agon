import pprint
import sys
import uuid

import database
from engine import PERSONAS, AgonEngine

database.init_db()

agent_configs = {}
models = [
    "openrouter/mistralai/mistral-nemo:free",
    "openrouter/google/gemini-2.5-flash:free",
    "gpt-4o-mini",
    "mock",
    "openrouter/anthropic/claude-3-haiku:free",
    "openrouter/meta-llama/llama-3-8b-instruct:free",
    "openrouter/x-ai/grok-beta:free",
]

for i, p in enumerate(PERSONAS):
    agent_configs[p["id"]] = {
        "api_key": "sk-test",
        "model_name": models[i % len(models)],
    }

print("Starting Agon Headless Verification (mock API keys)")
engine = AgonEngine(agent_configs=agent_configs)
session_id = str(uuid.uuid4())

seed_topic = "The security implications of self-modifying smart contracts."
turns = []

for _ in range(7):
    stream = engine.iter_turn_stream(turns, seed_topic)
    list(stream)

    metrics = engine.last_metrics
    database.insert_turn(
        session_id=session_id,
        persona_id=metrics["persona_id"],
        model_name=metrics["model_name"],
        raw_content=metrics["raw_content"],
        pattern_id=metrics["pattern_id"],
        ttft=metrics["ttft"],
        total_latency=metrics["total_latency"],
        token_count=metrics["token_count"],
        aggressiveness=metrics["aggressiveness"],
        happy=metrics["happy"],
        angry=metrics["angry"],
        sad=metrics["sad"],
        disrespect=metrics["disrespect"],
    )
    turns = database.get_turns(session_id)

print(f"\\n--- TURNS GENERATED (Session: {session_id}) ---")
for t in turns:
    print(
        f"[{t['persona_id']}] model={t['model_name']} | pattern={t['pattern_id']} | tokens={t['token_count']}"
    )

print("\\nVerification complete. DB writes successful.")
