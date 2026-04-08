# Team Setup Guide

## 1. Configure Environment Variables

```bash
# Copy the template (do this once)
cp .env.example .env

# Open .env and fill in your values
```

Edit `.env` with your actual credentials:

| Variable | What to set |
|---|---|
| `API_BASE_URL` | Leave as `http://localhost:7860` for local dev |
| `MODEL_NAME` | The HF model ID you want to use (e.g. `meta-llama/Meta-Llama-3-8B-Instruct`) |
| `HF_TOKEN` | Your personal Hugging Face access token |

## 2. Get Your Hugging Face Token

1. Go to [huggingface.co/settings/tokens](https://huggingface.co/settings/tokens)
2. Click **New token**
3. Give it a name (e.g. `netarena-dev`), select **Read** access
4. Copy the token (starts with `hf_`) and paste it into your `.env` file

## 3. Run the Project

```bash
# Terminal 1 — Start the environment server
uvicorn main:app --host 0.0.0.0 --port 7860

# Terminal 2 — Run the AI agent
# Load .env vars and launch (pick one method):
export $(grep -v '^#' .env | xargs) && python inference.py
```

## Security Rules

- **NEVER** commit the `.env` file. It is already in `.gitignore` — do not remove it.
- **NEVER** hardcode tokens or API keys in `inference.py` or any other source file.
- **NEVER** paste tokens in Slack, Discord, or issue trackers.
- If you suspect a token has been exposed, revoke it immediately at [huggingface.co/settings/tokens](https://huggingface.co/settings/tokens) and generate a new one.
