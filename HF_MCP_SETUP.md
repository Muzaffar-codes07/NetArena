# Hugging Face MCP Setup (Windows)

This project environment now includes Hugging Face MCP support via:

- `huggingface_hub[mcp]==1.9.1`

## 1) Set your Hugging Face token

In PowerShell:

```powershell
$env:HF_TOKEN = "hf_your_token_here"
```

## 2) Validate install

```powershell
.\.venv\Scripts\python.exe -c "from huggingface_hub import MCPClient; print('MCPClient import OK')"
```

## 3) Run a Tiny Agent (MCP-enabled CLI)

```powershell
.\.venv\Scripts\tiny-agents.exe run julien-c/flux-schnell-generator
```

When prompted, type your request (example: `Generate an image of a red panda in a cyberpunk city`).

## 4) Enable MCP directly in VS Code chat

This repo now includes workspace MCP wiring in `.vscode/mcp.json`.

1. Open Command Palette and run `MCP: List Servers`.
2. Start `hfFluxSchnell`.
3. When prompted, enter your Hugging Face token.
4. Open Chat and use tools from the `hfFluxSchnell` server.

To make this available across devices/platforms:

- Keep `.vscode/mcp.json` committed to git for workspace portability.
- Optionally enable Settings Sync and include MCP Servers.

## Notes

- `HF_TOKEN` is required for model inference.
- MCP support in `huggingface_hub` is experimental and may change across versions.
- If you open a new terminal, set `HF_TOKEN` again unless you persist it in your shell profile.
