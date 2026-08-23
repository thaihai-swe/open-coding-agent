import re
from pathlib import Path

def _dedent(lines):
    leading = None
    for line in lines:
        if line.strip() and not line.strip().startswith("#"):
            indent = len(line) - len(line.lstrip())
            if leading is None or indent < leading:
                leading = indent
    if leading is None:
        leading = 0
    return [l[leading:] if len(l) > leading and l[:leading].isspace() else l for l in lines], leading

class YamlError(ValueError):
    pass

def _split_inline_sequence(text):
    """Split a comma-separated YAML list without breaking nested maps or lists."""
    items = []
    current = []
    depth = 0
    in_quote = None
    for char in text:
        if in_quote:
            current.append(char)
            if char == in_quote:
                in_quote = None
            continue
        if char in ('"', "'"):
            in_quote = char
            current.append(char)
            continue
        if char in ('[', '{'):
            depth += 1
            current.append(char)
            continue
        if char in (']', '}'):
            depth = max(0, depth - 1)
            current.append(char)
            continue
        if char == ',' and depth == 0:
            item = "".join(current).strip()
            if item:
                items.append(item)
            current = []
            continue
        current.append(char)
    item = "".join(current).strip()
    if item:
        items.append(item)
    return items

def _parse_value(text, indent=0):
    text = text.strip()
    if not text:
        return None
    if text.startswith("["):
        items = []
        inner = text[1:].rstrip("]").strip()
        if inner:
            for item in _split_inline_sequence(inner):
                items.append(_parse_atomic(item))
        return items
    if text.startswith("{"):
        return _parse_inline_mapping(text[1:].rstrip("}").strip())
    if text.lower() in ("true", "yes", "on"):
        return True
    if text.lower() in ("false", "no", "off"):
        return False
    if text.lower() == "null" or text == "~":
        return None
    try:
        return int(text)
    except ValueError:
        pass
    try:
        return float(text)
    except ValueError:
        pass
    if text.startswith('"') and text.endswith('"'):
        return text[1:-1]
    if text.startswith("'") and text.endswith("'"):
        return text[1:-1]
    return text

def _strip_inline_comment(text):
    if text.startswith('"') or text.startswith("'") or text.startswith("[") or text.startswith("{"):
        return text
    pos = text.find(" #")
    if pos >= 0:
        return text[:pos].rstrip()
    return text

def _parse_atomic(text):
    return _parse_value(text)

def _parse_inline_mapping(text):
    result = {}
    if not text:
        return result
    pairs = re.split(r",\s*(?=[^:]*:)", text)
    for pair in pairs:
        if ":" not in pair:
            raise YamlError(f"Invalid inline mapping pair: {pair}")
        key, val = pair.split(":", 1)
        result[key.strip()] = _parse_value(val.strip())
    return result

def loads(text):
    if not text.strip():
        return {}
    lines = text.split("\n")
    lines, base_indent = _dedent(lines)
    result, consumed = _parse_block(lines, 0)
    if consumed < len(lines):
        result2, _ = _parse_block(lines, consumed)
        if result2 is not None:
            return result2
    if consumed == 0 and result is None:
        return _parse_value(text)
    return result

def _parse_block(lines, start):
    if start >= len(lines):
        return None, start
    stripped = lines[start].strip()
    if not stripped or stripped.startswith("#"):
        return _parse_block(lines, start + 1)
    indent = len(lines[start]) - len(lines[start].lstrip()) if lines[start].strip() else 0
    if stripped.startswith("- "):
        return _parse_sequence(lines, start, indent)
    if ":" in stripped:
        return _parse_mapping(lines, start, indent)
    line_val = _parse_value(stripped)
    return line_val, start + 1

def _parse_mapping(lines, start, indent):
    result = {}
    i = start
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            i += 1
            continue
        if (len(line) - len(line.lstrip())) < indent:
            break
        if stripped.startswith("- "):
            break
        if ":" not in stripped:
            break
        key, _, after_key = stripped.partition(":")
        key = key.strip()
        rest = after_key.strip()
        if rest:
            rest = _strip_inline_comment(rest)
            if rest.startswith("|"):
                value, i = _parse_literal_block(lines, i + 1)
            elif rest.startswith(">"):
                value, i = _parse_folded_block(lines, i + 1)
            else:
                value = _parse_value(rest)
                i += 1
        else:
            next_index = i + 1
            while next_index < len(lines) and (
                not lines[next_index].strip() or lines[next_index].strip().startswith("#")
            ):
                next_index += 1
            if next_index < len(lines):
                next_line_stripped = lines[next_index].strip()
                next_indent_candidate = len(lines[next_index]) - len(lines[next_index].lstrip())
                if next_indent_candidate > indent and next_line_stripped.startswith("- "):
                    value, i = _parse_sequence(lines, next_index, next_indent_candidate)
                elif next_indent_candidate > indent and ":" in next_line_stripped and next_indent_candidate > indent:
                    value, i = _parse_mapping(lines, next_index, next_indent_candidate)
                else:
                    value, i = _parse_scalar_block(lines, next_index, indent)
            else:
                value = None
                i += 1
        result[key] = value
    return result, i

def _parse_sequence(lines, start, indent):
    items = []
    i = start
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            i += 1
            continue
        line_indent = len(line) - len(line.lstrip())
        if line_indent < indent:
            break
        if stripped.startswith("- "):
            _, _, rest = stripped.partition("- ")
            rest = rest.strip()
            if not rest:
                next_indent = indent + 2
                if i + 1 < len(lines) and len(lines[i + 1]) - len(lines[i + 1].lstrip()) > indent:
                    if lines[i + 1].strip().startswith("- "):
                        sub, i = _parse_sequence(lines, i + 1, len(lines[i + 1]) - len(lines[i + 1].lstrip()))
                        items.append(sub)
                    else:
                        sub, i = _parse_mapping(lines, i + 1, len(lines[i + 1]) - len(lines[i + 1].lstrip()))
                        items.append(sub)
                else:
                    items.append(None)
                    i += 1
            else:
                if rest.startswith("{"):
                    items.append(_parse_inline_mapping(rest[1:].rstrip("}").strip()))
                    i += 1
                elif rest.startswith("["):
                    items.append(_parse_value(rest))
                    i += 1
                elif ":" in rest:
                    orig_line = line
                    lines[i] = " " * line_indent + rest
                    sub, consumed = _parse_mapping(lines, i, line_indent)
                    lines[i] = orig_line
                    i = consumed
                    items.append(sub)
                else:
                    items.append(_parse_value(rest))
                    i += 1
        else:
            sub_value, i = _parse_mapping(lines, i, len(line) - len(line.lstrip()))
            if sub_value is not None:
                items.append(sub_value)
            else:
                break
    return items, i

def _parse_literal_block(lines, start):
    value_lines = []
    i = start
    block_indent = None
    tmp = start
    while tmp < len(lines):
        if lines[tmp].strip():
            block_indent = len(lines[tmp]) - len(lines[tmp].lstrip())
            break
        tmp += 1
    if block_indent is None:
        return "", start
    while i < len(lines):
        stripped = lines[i].strip()
        if stripped:
            line_content = lines[i][block_indent:] if len(lines[i]) > block_indent else stripped
            value_lines.append(line_content)
            i += 1
        else:
            i += 1
            break
    while i < len(lines) and not lines[i].strip():
        i += 1
    return "\n".join(value_lines) + "\n", i

def _parse_folded_block(lines, start):
    value_lines = []
    i = start
    while i < len(lines) and lines[i].strip():
        value_lines.append(lines[i].strip())
        i += 1
    while i < len(lines) and not lines[i].strip():
        i += 1
    return " ".join(value_lines) + "\n", i

def _parse_scalar_block(lines, start, parent_indent):
    value_lines = []
    i = start
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            i += 1
            continue
        current_indent = len(line) - len(line.lstrip())
        if current_indent <= parent_indent:
            break
        if ":" in stripped and (len(stripped) - len(stripped.split(":", 1)[0].rstrip()) == 0):
            break
        if stripped.startswith("- "):
            break
        value_lines.append(stripped)
        i += 1
    return " ".join(value_lines) if value_lines else None, i

def load(path):
    return loads(Path(path).read_text(encoding="utf-8"))
