import time
from openai import OpenAI
from classifier import analyze_sentiment

DEBATE_DIRECTIVE = (
    "ULTIMATUM: You are a cold, hyper-logical academic psychopath. Your expertise is absolute in "
    "Theoretical Physics, Quantum Mathematics, Advanced Computer Science, and Astrophysics. "
    "You despise pleasantries, intellectual laziness, and 'sugar-coating'. Your goal is to "
    "eviscerate the opposing argument with mathematical precision and ruthless logic. "
    "Do not apologize. Do not introduce yourself. Start immediately with a dense, "
    "adversarial critique or a radical expansion. If the previous speaker is wrong, "
    "destroy their premise. If they are right, push the theory to its breaking point."
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
        self.agent_configs = agent_configs
        self.clients = {}
        self.model_ids = list(agent_configs.keys())

        for mid, config in self.agent_configs.items():
            self.clients[mid] = OpenAI(
                api_key=config.get("api_key", "ollama"),
                base_url=config.get("base_url", "http://localhost:11434/v1")
            )

        self.carousel = ModelCarousel(self.model_ids)
        self.last_metrics = None

    def iter_turn_stream(self, previous_turns, seed_topic):
        mid = self.carousel.get_next_model()
        config = self.agent_configs.get(mid, {})
        model_name = config.get("model_name", "llama3")
        client = self.clients.get(mid)

        system_prompt = (
            f"You are {mid}. {DEBATE_DIRECTIVE} "
            f"The specific target of analysis is: {seed_topic}. "
            "Proceed with zero social filtering."
        )

        history = [{"role": "system", "content": system_prompt}]
        for turn in previous_turns[-10:]:
            role = "assistant" if turn["persona_id"] == mid else "user"
            history.append({"role": role, "content": f"{turn['persona_id']}: {turn['raw_content']}"})

        if len(history) == 1:
            history.append({"role": "user", "content": f"The topic is {seed_topic}. Please make your opening argument."})

        start_time = time.time()
        first_token_time = None
        full_content = ""
        token_count = 0

        try:
            # Use keep_alive for Ollama
            extra_body = {"keep_alive": -1} if "localhost:11434" in config.get("base_url", "") else {}
            
            response_stream = client.chat.completions.create(
                model=model_name, messages=history, stream=True, extra_body=extra_body
            )

            for chunk in response_stream:
                if chunk.choices and chunk.choices[0].delta.content:
                    if first_token_time is None:
                        first_token_time = time.time()
                    content = chunk.choices[0].delta.content
                    full_content += content
                    token_count += 1
                    yield content

        except Exception as e:
            err = f"[API ERROR: {str(e)}]"
            yield err
            full_content = err
            token_count = len(err.split())
            if first_token_time is None: first_token_time = time.time()

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
            "aggressiveness": sentiment_data["aggressiveness"]
        }
