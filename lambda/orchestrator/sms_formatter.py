"""
SMS-Friendly Response Formatter
Converts rich responses to plain ASCII text for SMS delivery

AWS End User Messaging SMS API rejects messages with:
- Emojis and special unicode characters
- Certain control characters
- Messages exceeding 1600 characters

This formatter ensures all responses are SMS-safe.
"""
import re
import logging
from typing import Optional

logger = logging.getLogger()

# ============================================================================
# EMOJI TO TEXT MAPPINGS
# Replace common emojis with text equivalents to preserve meaning
# ============================================================================
EMOJI_TEXT_MAP = {
    # Weather emojis
    '\u2600\ufe0f': '(sunny)',      # ☀️
    '\u2600': '(sunny)',             # ☀
    '\u26c5': '(partly cloudy)',     # ⛅
    '\U0001f324': '(mostly sunny)',  # 🌤
    '\U0001f325': '(partly cloudy)', # 🌥
    '\u2601\ufe0f': '(cloudy)',      # ☁️
    '\u2601': '(cloudy)',            # ☁
    '\U0001f326': '(rain)',          # 🌦
    '\U0001f327': '(rainy)',         # 🌧
    '\u26c8': '(stormy)',            # ⛈
    '\U0001f329': '(lightning)',     # 🌩
    '\U0001f328': '(snow)',          # 🌨
    '\u2744\ufe0f': '(snow)',        # ❄️
    '\u2744': '(snow)',              # ❄
    '\U0001f32b': '(foggy)',         # 🌫
    '\U0001f32c': '(windy)',         # 🌬

    # Status emojis
    '\u26a0\ufe0f': '[!]',           # ⚠️
    '\u26a0': '[!]',                 # ⚠
    '\u2705': '[OK]',                # ✅
    '\u2714\ufe0f': '[OK]',          # ✔️
    '\u2714': '[OK]',                # ✔
    '\u274c': '[X]',                 # ❌
    '\u274e': '[X]',                 # ❎
    '\u2716\ufe0f': '[X]',           # ✖️
    '\u2716': '[X]',                 # ✖
    '\u2757': '[!]',                 # ❗
    '\u2755': '[!]',                 # ❕
    '\u2753': '[?]',                 # ❓
    '\u2754': '[?]',                 # ❔
    '\U0001f6a8': '[ALERT]',         # 🚨

    # Common UI emojis
    '\U0001f4c5': '',                # 📅 calendar - remove
    '\U0001f4c6': '',                # 📆 calendar - remove
    '\U0001f551': '',                # 🕑 clock - remove
    '\U0001f4cd': '',                # 📍 location pin - remove
    '\U0001f3e0': '',                # 🏠 house - remove
    '\U0001f527': '',                # 🔧 wrench - remove
    '\U0001f6e0': '',                # 🛠 tools - remove
    '\U0001f4de': '',                # 📞 phone - remove
    '\U0001f4e7': '',                # 📧 email - remove
    '\U0001f44d': '(OK)',            # 👍
    '\U0001f44e': '(NO)',            # 👎
    '\U0001f389': '',                # 🎉 party - remove
    '\U0001f31f': '',                # 🌟 star - remove
    '\u2b50': '',                    # ⭐ star - remove
}

# ============================================================================
# UNICODE TO ASCII MAPPINGS
# Replace special unicode characters with ASCII equivalents
# ============================================================================
UNICODE_ASCII_MAP = {
    # Quotes
    '\u2018': "'",   # '
    '\u2019': "'",   # '
    '\u201c': '"',   # "
    '\u201d': '"',   # "
    '\u201a': ',',   # ‚
    '\u201e': '"',   # „
    '\u2032': "'",   # ′
    '\u2033': '"',   # ″
    '\u00ab': '"',   # «
    '\u00bb': '"',   # »

    # Dashes
    '\u2013': '-',   # –
    '\u2014': '-',   # —
    '\u2015': '-',   # ―
    '\u2010': '-',   # ‐
    '\u2011': '-',   # ‑
    '\u2012': '-',   # ‒

    # Spaces
    '\u00a0': ' ',   # non-breaking space
    '\u2002': ' ',   # en space
    '\u2003': ' ',   # em space
    '\u2009': ' ',   # thin space
    '\u200a': ' ',   # hair space
    '\u200b': '',    # zero-width space
    '\u200c': '',    # zero-width non-joiner
    '\u200d': '',    # zero-width joiner
    '\ufeff': '',    # BOM

    # Other punctuation
    '\u2026': '...',  # …
    '\u2022': '*',    # •
    '\u2023': '>',    # ‣
    '\u2043': '-',    # ⁃
    '\u00b7': '*',    # ·
    '\u00b0': ' degrees',  # °
    '\u2103': 'C',    # ℃
    '\u2109': 'F',    # ℉

    # Arrows
    '\u2192': '->',   # →
    '\u2190': '<-',   # ←
    '\u2191': '^',    # ↑
    '\u2193': 'v',    # ↓
    '\u21d2': '=>',   # ⇒
    '\u21d0': '<=',   # ⇐
}


# Placeholder for protected project numbers (no underscores to avoid markdown issues)
_PROJECT_NUMBER_PLACEHOLDER = "[[PROJNUM{}]]"
_protected_project_numbers = {}


def _protect_project_numbers(text: str) -> str:
    """
    Detect and protect project numbers before markdown removal.

    Project numbers have patterns like:
    - 21083_09PF05VD_1762166550719
    - 21083_09PF05VD_1762166550719_1_1_1
    - Alphanumeric segments separated by underscores
    """
    global _protected_project_numbers
    _protected_project_numbers = {}

    # Pattern: 2+ segments of alphanumeric separated by underscores
    # Must have at least one underscore and contain both letters and numbers
    # Use lookahead/lookbehind to also match inside markdown (e.g., **proj_num**)
    project_pattern = re.compile(
        r'(?<![A-Za-z0-9_])([A-Za-z0-9]+(?:_[A-Za-z0-9]+){2,})(?![A-Za-z0-9_])'
    )

    def replace_with_placeholder(match):
        project_num = match.group(1)
        # Only protect if it looks like a project number (has both letters and digits)
        has_letters = any(c.isalpha() for c in project_num)
        has_digits = any(c.isdigit() for c in project_num)
        if has_letters and has_digits:
            idx = len(_protected_project_numbers)
            placeholder = _PROJECT_NUMBER_PLACEHOLDER.format(idx)
            _protected_project_numbers[placeholder] = project_num
            logger.debug(f"[SMS] Protected project number: {project_num} -> {placeholder}")
            return placeholder
        return project_num

    return project_pattern.sub(replace_with_placeholder, text)


def _restore_project_numbers(text: str) -> str:
    """Restore protected project numbers after markdown removal."""
    global _protected_project_numbers
    for placeholder, project_num in _protected_project_numbers.items():
        text = text.replace(placeholder, project_num)
    _protected_project_numbers = {}
    return text


def format_for_sms(response_text: str, max_length: int = 1500) -> str:
    """
    Format response for SMS delivery - plain ASCII, no emojis.

    Args:
        response_text: Raw response from orchestrator
        max_length: Maximum message length (default 1500, SMS max is 1600)

    Returns:
        SMS-safe plain text response
    """
    if not response_text:
        return response_text

    try:
        text = response_text

        # Step 0: Protect project numbers before any processing
        text = _protect_project_numbers(text)

        # Step 1: Replace known emojis with text equivalents
        text = _replace_emojis_with_text(text)

        # Step 2: Strip any remaining emojis
        text = _strip_remaining_emojis(text)

        # Step 3: Remove markdown formatting
        text = _remove_markdown(text)

        # Step 4: Restore protected project numbers
        text = _restore_project_numbers(text)

        # Step 5: Replace special unicode with ASCII
        text = _normalize_unicode(text)

        # Step 6: Clean up whitespace
        text = _compact_whitespace(text)

        # Step 7: Truncate if too long
        text = _truncate_message(text, max_length)

        # Step 8: Final ASCII-only cleanup
        text = _ensure_ascii_safe(text)

        logger.info(f"[SMS] Formatted response: {len(response_text)} -> {len(text)} chars")

        return text.strip()

    except Exception as e:
        logger.error(f"[SMS] Error formatting for SMS: {e}")
        # Return a safe fallback - strip everything non-ASCII
        return _ensure_ascii_safe(response_text)[:max_length]


def _replace_emojis_with_text(text: str) -> str:
    """Replace known emojis with text equivalents."""
    for emoji, replacement in EMOJI_TEXT_MAP.items():
        text = text.replace(emoji, replacement)
    return text


def _strip_remaining_emojis(text: str) -> str:
    """Remove any remaining emoji characters."""
    # Comprehensive emoji regex pattern
    emoji_pattern = re.compile(
        "["
        "\U0001F600-\U0001F64F"  # emoticons
        "\U0001F300-\U0001F5FF"  # symbols & pictographs
        "\U0001F680-\U0001F6FF"  # transport & map symbols
        "\U0001F700-\U0001F77F"  # alchemical symbols
        "\U0001F780-\U0001F7FF"  # geometric shapes extended
        "\U0001F800-\U0001F8FF"  # supplemental arrows-c
        "\U0001F900-\U0001F9FF"  # supplemental symbols and pictographs
        "\U0001FA00-\U0001FA6F"  # chess symbols
        "\U0001FA70-\U0001FAFF"  # symbols and pictographs extended-a
        "\U00002702-\U000027B0"  # dingbats
        "\U0001F1E0-\U0001F1FF"  # flags (iOS)
        "\U00002600-\U000026FF"  # misc symbols
        "\U00002300-\U000023FF"  # misc technical
        "\U0000FE00-\U0000FE0F"  # variation selectors
        "\U0001F000-\U0001F02F"  # mahjong tiles
        "\U0001F0A0-\U0001F0FF"  # playing cards
        "]+",
        flags=re.UNICODE
    )
    return emoji_pattern.sub('', text)


def _remove_markdown(text: str) -> str:
    """Remove markdown formatting."""
    # Bold
    text = re.sub(r'\*\*(.+?)\*\*', r'\1', text)
    # Italic with asterisks
    text = re.sub(r'\*(.+?)\*', r'\1', text)
    # Bold with underscores
    text = re.sub(r'__(.+?)__', r'\1', text)
    # Italic with underscores
    text = re.sub(r'_(.+?)_', r'\1', text)
    # Code blocks
    text = re.sub(r'```.*?```', '', text, flags=re.DOTALL)
    # Inline code
    text = re.sub(r'`(.+?)`', r'\1', text)
    # Headers
    text = re.sub(r'^#+\s+', '', text, flags=re.MULTILINE)
    # Bullet points (convert to simple dash)
    text = re.sub(r'^\s*[-*]\s+', '- ', text, flags=re.MULTILINE)
    # Links [text](url) -> text
    text = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', text)
    # Images ![alt](url) -> remove
    text = re.sub(r'!\[[^\]]*\]\([^)]+\)', '', text)

    return text


def _normalize_unicode(text: str) -> str:
    """Replace special unicode characters with ASCII equivalents."""
    for unicode_char, ascii_char in UNICODE_ASCII_MAP.items():
        text = text.replace(unicode_char, ascii_char)
    return text


def _compact_whitespace(text: str) -> str:
    """Clean up excessive whitespace."""
    # Multiple spaces to single space
    text = re.sub(r'[ \t]+', ' ', text)
    # Multiple newlines to double newline max
    text = re.sub(r'\n{3,}', '\n\n', text)
    # Space before punctuation
    text = re.sub(r'\s+([.,!?;:])', r'\1', text)
    # Double punctuation from emoji removal
    text = re.sub(r'([.,!?;:])\s*\1+', r'\1', text)
    # Trim lines
    lines = [line.strip() for line in text.split('\n')]
    text = '\n'.join(lines)

    return text


def _truncate_message(text: str, max_length: int) -> str:
    """Truncate message to max length, preserving word boundaries."""
    if len(text) <= max_length:
        return text

    # Try to break at sentence boundary
    truncated = text[:max_length - 3]  # Leave room for "..."

    # Find last sentence end
    last_period = truncated.rfind('. ')
    last_question = truncated.rfind('? ')
    last_exclaim = truncated.rfind('! ')

    best_break = max(last_period, last_question, last_exclaim)

    if best_break > max_length * 0.5:  # Only use if we keep at least half
        return truncated[:best_break + 1]

    # Otherwise break at word boundary
    last_space = truncated.rfind(' ')
    if last_space > max_length * 0.8:
        return truncated[:last_space] + '...'

    return truncated + '...'


def _ensure_ascii_safe(text: str) -> str:
    """Ensure text contains only ASCII-safe characters."""
    # Keep only printable ASCII and common whitespace
    result = []
    for char in text:
        if ord(char) < 128:  # ASCII range
            result.append(char)
        elif char in ' \n\t':
            result.append(char)
        # Skip everything else

    return ''.join(result)


def is_sms_channel(channel: Optional[str]) -> bool:
    """Check if the channel is SMS."""
    if not channel:
        return False
    return channel.lower() == 'sms'
