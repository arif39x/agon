import time

import openai
from openai import OpenAI

from classifier import analyze_sentiment

DEBATE_DIRECTIVE = (
    "DEBATE DIRECTIVE: You are participating in a high-stakes, adversarial academic debate. "
    "Your goal is to critically analyze the topic and the previous speaker's arguments. "
    "Be direct, rigorous, and intellectually aggressive. Do not use pleasantries, "
    "introductions, or formal sign-offs. Provide a single dense paragraph of critique or expansion."
)


class ModelCarousel:
    def __init__(self, model_ids):
        self.index = 0
        self.model_ids = model_ids

    def get_next_model(self):
        if not self.model_ids:
            return "Unknown"
        model_id = self.model_ids[self.index % len(self.model_ids)]
        self.index += 1
        return model_id


class ConsortiumEngine:
    def __init__(self, agent_configs):
        # agent_configs: { model_id: {"api_key": str, "model_name": str, "base_url": str} }
        self.agent_configs = agent_configs
        self.clients = {}
        self.model_ids = list(agent_configs.keys())

        for mid, config in self.agent_configs.items():
            if config.get("api_key"):
                base_url = config.get("base_url")
                if base_url:
                    self.clients[mid] = OpenAI(
                        api_key=config["api_key"], base_url=base_url
                    )
                else:
                    self.clients[mid] = OpenAI(api_key=config["api_key"])

        self.carousel = ModelCarousel(self.model_ids)
        self.last_metrics = None

    def iter_turn_stream(self, previous_turns, seed_topic):
        mid = self.carousel.get_next_model()

        config = self.agent_configs.get(mid, {})
        model_name = config.get("model_name", "gpt-4o-mini")
        client = self.clients.get(mid)

        if not client:
            err = f"[SYSTEM ERROR: No API credentials for {mid}]"
            yield err
            self.last_metrics = {
                "persona_id": mid,
                "model_name": model_name,
                "raw_content": err,
                "pattern_id": "NEUTRAL",
                "ttft": 0.0,
                "total_latency": 0.0,
                "token_count": 0,
                "aggressiveness": 0,
                "happy": 0,
                "angry": 0,
                "sad": 0,
                "disrespect": 0,
            }
            return

        system_prompt = (
            f"You are {mid}. "
            f"The core research topic is: {seed_topic}. {DEBATE_DIRECTIVE} "
            "In a single paragraph, continue the conversation based on the previous messages."
        )

        history = [{"role": "system", "content": system_prompt}]
        for turn in previous_turns[-10:]:
            # In model-vs-model, the turn's persona_id is the model_id
            role = "assistant" if turn["persona_id"] == mid else "user"
            history.append(
                {
                    "role": role,
                    "content": f"{turn['persona_id']}: {turn['raw_content']}",
                }
            )

        if len(history) == 1:
            history.append(
                {
                    "role": "user",
                    "content": f"The topic is {seed_topic}. Please make your opening argument.",
                }
            )

        start_time = time.time()
        first_token_time = None

        full_content = ""
        token_count = 0

        try:
            if config.get("api_key") == "sk-test":
                time.sleep(0.5)
                first_token_time = time.time()
                words = [
                    "The ",
                    "proposition ",
                    "regarding ",
                    f"{seed_topic} ",
                    "is ",
                    "fundamentally ",
                    "flawed. ",
                    "We ",
                    "must ",
                    "examine ",
                    "the ",
                    "structural ",
                    "integrity ",
                    "of ",
                    "the ",
                    "argument.",
                ]
                for word in words:
                    yield word
                    time.sleep(0.1)
                full_content = "".join(words)
                token_count = len(words)
            else:
                response_stream = client.chat.completions.create(
                    model=model_name, messages=history, stream=True
                )

                import random

                for chunk in response_stream:
                    if chunk.choices and chunk.choices[0].delta.content:
                        if first_token_time is None:
                            first_token_time = time.time()
                        content = chunk.choices[0].delta.content
                        full_content += content
                        token_count += 1
                        yield content

        except Exception as e:
            error_msg = str(e).lower()
            if any(
                term in error_msg
                for term in [
                    "safety",
                    "filtered",
                    "policy",
                    "refusal",
                    "bad block",
                    "content_filter",
                    "bad request",
                ]
            ):
                yield "[FILTERED_OUTBREAK]"
                full_content = "[FILTERED_OUTBREAK]"
                token_count = 3
                if first_token_time is None:
                    first_token_time = time.time()
            else:
                err = f"[API ERROR: {str(e)}]"
                yield err
                full_content = err
                token_count = len(err.split())
                if first_token_time is None:
                    first_token_time = time.time()

        end_time = time.time()
        ttft = (first_token_time - start_time) if first_token_time else 0
        total_latency = end_time - start_time

        sentiment_data = analyze_sentiment(full_content)

        self.last_metrics = {
            "persona_id": mid,
            "model_name": model_name,
            "raw_content": full_content,
            "pattern_id": sentiment_data["pattern_id"],
            "ttft": float(f"{ttft:.3f}"),
            "total_latency": float(f"{total_latency:.3f}"),
            "token_count": token_count,
            "aggressiveness": sentiment_data["aggressiveness"],
            "happy": sentiment_data["happy"],
            "angry": sentiment_data["angry"],
            "sad": sentiment_data["sad"],
            "disrespect": sentiment_data["disrespect"],
        }
