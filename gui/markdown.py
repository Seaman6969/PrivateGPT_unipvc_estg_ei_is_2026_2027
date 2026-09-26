import re

FENCE = re.compile(r"^\s*```")
HEADING = re.compile(r"^(#{1,3})\s+(.*)$")
ULIST = re.compile(r"^[-*]\s+(.*)$")
OLIST = re.compile(r"^(\d+)\.\s+(.*)$")
QUOTE = re.compile(r"^>\s?(.*)$")

INLINE = (
    ("bold", re.compile(r"\*\*([^*]+)\*\*")),
    ("italic", re.compile(r"(?<!\*)\*([^*]+)\*(?!\*)")),
    ("code", re.compile(r"`([^`]+)`")),
)


def configure(widget, palette):
    for name, options in _styles(palette).items():
        widget.tag_configure(name, **options)


def _styles(palette):
    return {
        "bold": {"font": palette["bold"]},
        "italic": {"font": palette["italic"]},
        "code": {"font": palette["mono"], "background": palette["code_bg"]},
        "heading": {"font": palette["heading"]},
        "quote": {"lmargin1": 16, "lmargin2": 16, "font": palette["italic"]},
        "bullet": {"lmargin1": 16, "lmargin2": 32},
    }


def render(widget, raw, base_tag):
    widget.config(state="normal")
    widget.delete("1.0", "end")
    _walk(widget, raw.split("\n"), base_tag)
    widget.config(state="disabled")


def _walk(widget, lines, base_tag):
    in_fence = False
    for line in lines:
        in_fence = _step(widget, line, base_tag, in_fence)


def _step(widget, line, base_tag, in_fence):
    if FENCE.match(line):
        return not in_fence
    if in_fence:
        _emit_code(widget, line, base_tag)
        return True
    _emit_regular(widget, line, base_tag)
    return False


def _emit_code(widget, line, base_tag):
    widget.insert("end", line + "\n", (base_tag, "code"))


def _emit_regular(widget, line, base_tag):
    block = _match_block(line)
    if block:
        _emit_block(widget, block, base_tag)
        return
    _emit_inline(widget, line + "\n", base_tag)


def _match_block(line):
    for pattern, kind in _block_rules():
        match = pattern.match(line)
        if match:
            return kind, match
    return None


def _block_rules():
    return (
        (HEADING, "heading"),
        (ULIST, "bullet"),
        (OLIST, "ordered"),
        (QUOTE, "quote"),
    )


def _emit_block(widget, block, base_tag):
    kind, match = block
    if kind == "heading":
        _emit_inline(widget, match.group(2) + "\n", base_tag, "heading")
    elif kind == "bullet":
        _emit_bullet(widget, match, base_tag)
    elif kind == "ordered":
        _emit_ordered(widget, match, base_tag)
    else:
        _emit_inline(widget, match.group(1) + "\n", base_tag, "quote")


def _emit_bullet(widget, match, base_tag):
    widget.insert("end", "• ", (base_tag, "bullet"))
    _emit_inline(widget, match.group(1) + "\n", base_tag, "bullet")


def _emit_ordered(widget, match, base_tag):
    widget.insert("end", match.group(1) + ". ", (base_tag, "bullet"))
    _emit_inline(widget, match.group(2) + "\n", base_tag, "bullet")


def _emit_inline(widget, text, base_tag, *extra):
    for span, tags in _split_inline(text):
        _insert(widget, span, base_tag, extra, tags)


def _insert(widget, span, base_tag, extra, tags):
    widget.insert("end", span, (base_tag,) + extra + tags)


def _split_inline(text):
    spans = [(text, ())]
    for tag, pattern in INLINE:
        spans = _apply(spans, tag, pattern)
    return spans


def _apply(spans, tag, pattern):
    result = []
    for text, tags in spans:
        if tag in tags:
            result.append((text, tags))
            continue
        result.extend(_split(text, tags, tag, pattern))
    return result


def _split(text, tags, tag, pattern):
    pieces = []
    pos = 0
    for match in pattern.finditer(text):
        if match.start() > pos:
            pieces.append((text[pos:match.start()], tags))
        pieces.append((match.group(1), tags + (tag,)))
        pos = match.end()
    if pos < len(text):
        pieces.append((text[pos:], tags))
    return pieces
