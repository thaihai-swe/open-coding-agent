# Running and Testing

## Virtual Environment Setup

1. Create a Python virtual environment:
   ```bash
   python3 -m venv .venv
   ```
2. Activate it:
   ```bash
   source .venv/bin/activate
   ```

## Running the Application

Create the ignored secret configuration file:

```bash
mkdir -p .cda/.secrets
cp documents/config.example.json .cda/.secrets/config.json
chmod 600 .cda/.secrets/config.json
```

Edit `.cda/.secrets/config.json` with your provider settings. The application reads this file by default. You can use another path with `CONFIG_FILE=/path/to/config.json`.

Environment variables override JSON values when set: `OPENAI_API_BASE`, `OPENAI_API_KEY`, and `OPENAI_MODEL`.

Start the REPL:

```bash
python3 -m src.cli
```

Resume a previous session:

```bash
python3 -m src.cli --session <session-id>
```

Run in JSON mode:

```bash
python3 -m src.cli --json
```

Show full Python tracebacks when diagnosing provider or tool errors:

```bash
python3 -m src.cli --debug
```

Use `--debug` when an API-compatible server returns an unexpected response. Check that the configured endpoint supports `/chat/completions` and that the selected model is valid.

## Running Tests and Verification

Validate imports and run unit checks inside the environment:

```bash
python3 -m py_compile src/**/*.py
python3 tests/provider_check.py
python3 tests/session_check.py
python3 tests/query_engine_check.py
python3 tests/terminal_ui_check.py
python3 tests/cli_check.py
```
