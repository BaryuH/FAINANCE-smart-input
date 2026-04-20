import re
import json
from typing import Any


def extract_json_from_text(text: str) -> Any:
    """Extract and parse JSON from a text blob.

    Handles fenced Markdown code blocks (```json ... ``` or ``` ... ```),
    extracts the first JSON object or array found, and attempts a couple of
    common recovery heuristics (replace single quotes, remove trailing commas).

    Raises ValueError if parsing fails.
    """
    if not isinstance(text, str):
        raise ValueError("Input must be a string")

    # 1) Look for fenced code block (```json ... ``` or ``` ... ```)
    m = re.search(r"```(?:json)?\s*([\s\S]*?)```", text, flags=re.IGNORECASE)
    if m:
        candidate = m.group(1).strip()
    else:
        candidate = text.strip()

    # 3) Try parsing. If the candidate contains extra text or multiple JSON
    # objects, attempt to find and parse individual JSON object/array
    # candidates (non-greedy) and return the first successful parse.
    parse_attempts = []

    def try_parse(s: str):
        try:
            return json.loads(s)
        except Exception:
            return None

    # First, try parsing the whole candidate as-is
    parsed = try_parse(candidate)
    if parsed is not None:
        return parsed

    # Recovery: replace single quotes and remove trailing commas, then try whole
    fixed_whole = candidate.replace("'", '"')
    fixed_whole = re.sub(r",\s*([}\]])", r"\1", fixed_whole)
    parsed = try_parse(fixed_whole)
    if parsed is not None:
        return parsed

    # Next, search for JSON object matches { ... } non-greedy and try each
    for mobj in re.finditer(r"\{[\s\S]*?\}", candidate):
        snippet = mobj.group(0)
        parsed = try_parse(snippet)
        if parsed is not None:
            return parsed
        # try fixed variant
        fixed = snippet.replace("'", '"')
        fixed = re.sub(r",\s*([}\]])", r"\1", fixed)
        parsed = try_parse(fixed)
        if parsed is not None:
            return parsed

    # Then try JSON arrays
    for marr in re.finditer(r"\[[\s\S]*?\]", candidate):
        snippet = marr.group(0)
        parsed = try_parse(snippet)
        if parsed is not None:
            return parsed
        fixed = snippet.replace("'", '"')
        fixed = re.sub(r",\s*([}\]])", r"\1", fixed)
        parsed = try_parse(fixed)
        if parsed is not None:
            return parsed

    # If nothing parsed, raise a helpful error
    raise ValueError("Failed to parse JSON: no valid JSON object/array found")


def extract_price_from_text(text: str) -> int:
    """Extract an integer price (VND) from free text.

    Handles numbers with separators (dots/commas) and common Vietnamese
    multipliers like 'k', 'ka', 'ca', 'nghìn', 'ngàn' (×1_000) and
    'tr', 'triệu', 'trieu' (×1_000_000).

    Returns 0 when no price can be found.
    """
    if not text:
        return 0

    s = text.lower()

    # Try number followed by unit first
    unit_map_thousand = {"k", "ka", "ca", "nghin", "ngan", "nghìn", "ngàn"}
    unit_map_million = {"tr", "trieu", "triệu", "triu", "trieu"}

    m = re.search(
        r"([\d\.,]+)\s*(k|ka|ca|nghin|ngan|nghìn|ngàn|tr|trieu|triệu|triu)\b",
        s,
        flags=re.IGNORECASE,
    )
    if m:
        num_raw = m.group(1)
        unit = m.group(2)
        digits = re.sub(r"[^0-9]", "", num_raw)
        if not digits:
            return 0
        try:
            base = int(digits)
        except Exception:
            return 0
        if unit in unit_map_thousand:
            return base * 1000
        if unit in unit_map_million:
            return base * 1000000

    # Fallback: find all numeric tokens and take the largest one (likely the amount)
    nums = re.findall(r"[\d\.,]+", s)
    if not nums:
        return 0

    # Normalize tokens by removing separators and converting to int
    candidates = []
    for tok in nums:
        digits = re.sub(r"[^0-9]", "", tok)
        if digits:
            try:
                candidates.append(int(digits))
            except Exception:
                continue

    if not candidates:
        return 0

    # Heuristic: prefer the largest candidate
    return max(candidates)
