CHARS_PER_TOKEN = 4.0

_ENCODING = None
_TOKENIZER_INITIALIZED = False

try:
    import tiktoken
except ImportError:
    tiktoken = None


def _get_encoding():
    """Return a local tokenizer when available without blocking startup."""
    global _ENCODING, _TOKENIZER_INITIALIZED
    if _TOKENIZER_INITIALIZED:
        return _ENCODING

    _TOKENIZER_INITIALIZED = True
    if tiktoken is None:
        return None

    try:
        _ENCODING = tiktoken.get_encoding("cl100k_base")
    except Exception:
        _ENCODING = None
    return _ENCODING


def estimate_tokens(text):
    if not text:
        return 0
    encoding = _get_encoding()
    if encoding is not None:
        return len(encoding.encode(text))
    return int(len(text) / CHARS_PER_TOKEN)


def tokenizer_mode():
    """Identify whether counts are exact or heuristic for honest diagnostics."""
    return "cl100k_base" if _get_encoding() is not None else "chars_per_token_estimate"
