# agon

## Setup

### 1. Prerequisites

- Rust
- Python 3.10+
- Ollama: https://ollama.com/ (Running at http://localhost:11434)

### 2. Python Setup

```bash
pip install -r requirements.txt
```

### 3. Build Core

```bash
cd core
cargo build --release
cd ..
```

## Usage

1. Start Ollama (ollama serve).
2. Run the platform:
   ```bash
   python src/app.py
   ```
3. Use the REFRESH button to find local models.
4. Select at least two models, define a scientific topic, and click INITIALIZE DEBATE.
