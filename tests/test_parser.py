"""
Unit and integration tests for CSSParser in parser.py.
Covers all required edge cases, syntax variations, at-rules, and error conditions.
"""

from pathlib import Path
import pytest

from parser import (
    AtRule,
    CSSFileNotFoundError,
    CSSParser,
    EmptyFileError,
    InvalidCSSFileError,
    KeyframeRule,
    QualifiedRule,
    parse_css,
    parse_css_file,
)


# ============================================================================
# Core Parser Tests
# ============================================================================

def test_1_normal_css_multiple_rules():
    """Case 1: Normal CSS file with multiple rules."""
    css = """
    h1 {
        font-size: 24px;
        color: #333333;
    }
    p {
        line-height: 1.5;
        margin-bottom: 16px;
    }
    """
    parsed = parse_css(css, source="normal.css")
    assert len(parsed.rules) == 2
    assert isinstance(parsed.rules[0], QualifiedRule)
    assert parsed.rules[0].selector == "h1"
    assert parsed.rules[0].declaration_count == 2
    assert parsed.rules[0].declarations[0].property == "font-size"
    assert parsed.rules[0].declarations[0].value == "24px"
    assert parsed.rules[0].declarations[1].property == "color"
    assert parsed.rules[0].declarations[1].value == "#333333"

    assert isinstance(parsed.rules[1], QualifiedRule)
    assert parsed.rules[1].selector == "p"
    assert parsed.rules[1].declaration_count == 2


def test_2_empty_file(tmp_path: Path):
    """Case 2: An empty file raises EmptyFileError."""
    empty_file = tmp_path / "empty.css"
    empty_file.write_text("", encoding="utf-8")

    with pytest.raises(EmptyFileError) as exc_info:
        parse_css_file(empty_file)
    assert "empty" in str(exc_info.value).lower()

    # Also test file with only whitespace
    whitespace_file = tmp_path / "whitespace.css"
    whitespace_file.write_text("   \n\t  \n  ", encoding="utf-8")
    with pytest.raises(EmptyFileError):
        parse_css_file(whitespace_file)


def test_3_comments_only_file():
    """Case 3: A file containing only comments."""
    css = """
    /* First comment block explaining stylesheet */
    /* Second comment block
       spanning multiple lines */
    """
    parsed = parse_css(css, source="comments.css")
    assert len(parsed.rules) == 0
    assert parsed.comments_count == 2
    assert len(parsed.diagnostics) == 0


def test_4_multiple_selectors_in_one_rule():
    """Case 4: Multiple selectors in one rule (preserves full string and split selectors)."""
    css = """
    .btn,
    .btn-primary,
    button[type="submit"],
    a.action-link:hover {
        padding: 8px 16px;
        cursor: pointer;
    }
    """
    parsed = parse_css(css)
    assert len(parsed.rules) == 1
    rule = parsed.rules[0]
    assert isinstance(rule, QualifiedRule)

    # Full selector preserves combined selector string
    assert ".btn" in rule.selector
    assert ".btn-primary" in rule.selector
    assert 'button[type="submit"]' in rule.selector
    assert "a.action-link:hover" in rule.selector

    # Split selectors properly tokenized without naive string splitting
    assert len(rule.selectors) == 4
    assert rule.selectors[0] == ".btn"
    assert rule.selectors[1] == ".btn-primary"
    assert rule.selectors[2] == 'button[type="submit"]'
    assert rule.selectors[3] == "a.action-link:hover"


def test_5_duplicate_declarations():
    """Case 5: Duplicate declarations (e.g. vendor prefixes, cascade fallbacks)."""
    css = """
    .box {
        display: -webkit-box;
        display: -ms-flexbox;
        display: flex;
        color: red;
        color: blue;
    }
    """
    parsed = parse_css(css)
    rule = parsed.rules[0]
    assert isinstance(rule, QualifiedRule)
    assert rule.declaration_count == 5

    # Order of declarations preserved exactly as authored
    props = [d.property for d in rule.declarations]
    values = [d.value for d in rule.declarations]
    assert props == ["display", "display", "display", "color", "color"]
    assert values == ["-webkit-box", "-ms-flexbox", "flex", "red", "blue"]


def test_6_important_declarations():
    """Case 6: !important declarations flagged correctly without polluting the value."""
    css = """
    .alert {
        color: #ff0000 !important;
        background-color: yellow;
        border: 1px solid red !important;
    }
    """
    parsed = parse_css(css)
    rule = parsed.rules[0]
    assert isinstance(rule, QualifiedRule)
    decls = rule.declarations

    assert decls[0].property == "color"
    assert decls[0].value == "#ff0000"
    assert decls[0].important is True

    assert decls[1].property == "background-color"
    assert decls[1].value == "yellow"
    assert decls[1].important is False

    assert decls[2].property == "border"
    assert decls[2].value == "1px solid red"
    assert decls[2].important is True


def test_7_values_containing_commas_and_parentheses():
    """Case 7: Values containing commas, spaces, and parentheses."""
    css = """
    .card {
        background-color: rgb(255, 0, 0);
        box-shadow: 0 10px 20px rgba(0, 0, 0, 0.2);
        background-image: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    }
    """
    parsed = parse_css(css)
    rule = parsed.rules[0]
    assert isinstance(rule, QualifiedRule)
    decls = {d.property: d.value for d in rule.declarations}

    assert decls["background-color"] == "rgb(255, 0, 0)"
    assert decls["box-shadow"] == "0 10px 20px rgba(0, 0, 0, 0.2)"
    assert decls["background-image"] == "linear-gradient(135deg, #667eea 0%, #764ba2 100%)"


def test_8_quoted_strings_containing_punctuation():
    """Case 8: Quoted strings containing commas, quotes, and punctuation."""
    css = """
    .text {
        font-family: "Helvetica Neue", "Segoe UI, Regular", Arial, sans-serif;
        content: "Warning: Value, (special: 100%);";
    }
    """
    parsed = parse_css(css)
    rule = parsed.rules[0]
    assert isinstance(rule, QualifiedRule)
    decls = {d.property: d.value for d in rule.declarations}

    assert decls["font-family"] == '"Helvetica Neue", "Segoe UI, Regular", Arial, sans-serif'
    assert decls["content"] == '"Warning: Value, (special: 100%);"'


def test_9_css_custom_properties():
    """Case 9: CSS custom properties (variables) with casing preserved."""
    css = """
    :root {
        --primary-color: #3498db;
        --base-font-size: 16px;
        --themeAccent: #e67e22;
        --complex-calc: calc(var(--base-font-size) * 1.25);
    }
    """
    parsed = parse_css(css)
    rule = parsed.rules[0]
    assert isinstance(rule, QualifiedRule)
    decls = {d.property: d.value for d in rule.declarations}

    assert decls["--primary-color"] == "#3498db"
    assert decls["--base-font-size"] == "16px"
    # Custom property case is preserved
    assert decls["--themeAccent"] == "#e67e22"
    assert decls["--complex-calc"] == "calc(var(--base-font-size) * 1.25)"


def test_10_nested_media_rules():
    """Case 10: Nested @media rules containing qualified rules."""
    css = """
    @media (max-width: 768px) {
        .container {
            width: 100%;
            padding: 0 10px;
        }
        .sidebar {
            display: none;
        }
    }
    """
    parsed = parse_css(css)
    assert len(parsed.rules) == 1
    media_rule = parsed.rules[0]
    assert isinstance(media_rule, AtRule)
    assert media_rule.at_keyword == "media"
    assert media_rule.prelude == "(max-width: 768px)"
    assert len(media_rule.rules) == 2

    child1 = media_rule.rules[0]
    assert isinstance(child1, QualifiedRule)
    assert child1.selector == ".container"
    assert child1.declaration_count == 2

    child2 = media_rule.rules[1]
    assert isinstance(child2, QualifiedRule)
    assert child2.selector == ".sidebar"
    assert child2.declaration_count == 1


def test_11_keyframes_selectors():
    """Case 11: @keyframes with from, to, and percentage selectors."""
    css = """
    @keyframes pulse {
        from {
            transform: scale(1);
            opacity: 1;
        }
        50% {
            transform: scale(1.1);
            opacity: 0.8;
        }
        to {
            transform: scale(1);
            opacity: 1;
        }
    }
    """
    parsed = parse_css(css)
    assert len(parsed.rules) == 1
    kf = parsed.rules[0]
    assert isinstance(kf, AtRule)
    assert kf.at_keyword == "keyframes"
    assert kf.prelude == "pulse"
    assert len(kf.rules) == 3

    assert isinstance(kf.rules[0], KeyframeRule)
    assert kf.rules[0].selector == "from"
    assert kf.rules[0].declaration_count == 2

    assert isinstance(kf.rules[1], KeyframeRule)
    assert kf.rules[1].selector == "50%"
    assert kf.rules[1].declaration_count == 2

    assert isinstance(kf.rules[2], KeyframeRule)
    assert kf.rules[2].selector == "to"
    assert kf.rules[2].declaration_count == 2


def test_12_malformed_css_recovery():
    """Case 12: Malformed CSS is reported via diagnostics without crashing."""
    css = """
    .valid-before {
        color: green;
    }
    .broken-rule {
        color: ;
        invalid declaration here
        margin: 10px;
    }
    .valid-after {
        font-weight: bold;
    }
    """
    parsed = parse_css(css)
    # Valid rules before and after should be parsed successfully
    assert len(parsed.rules) >= 2
    assert parsed.rules[0].selector == ".valid-before"
    assert parsed.rules[0].declarations[0].value == "green"

    # Diagnostics should capture malformed syntax
    assert len(parsed.diagnostics) > 0
    assert any("declaration" in d.message.lower() for d in parsed.diagnostics)


def test_13_missing_input_file():
    """Case 13: A missing input file raises CSSFileNotFoundError."""
    with pytest.raises(CSSFileNotFoundError) as exc_info:
        parse_css_file("this_file_does_not_exist_12345.css")
    assert "not found" in str(exc_info.value).lower()


def test_14_input_with_no_qualified_css_rules():
    """Case 14: An input with no qualified CSS rules (e.g. only @charset or @import)."""
    css = """
    @charset "UTF-8";
    @import url("reset.css");
    /* No qualified styling rules present */
    """
    parsed = parse_css(css)
    # At-rules are captured without creating phantom qualified rules
    assert len(parsed.rules) == 2
    assert parsed.rules[0].at_keyword == "charset"
    assert parsed.rules[1].at_keyword == "import"

    # Verify no qualified rules
    qualified_rules = [r for r in parsed.rules if isinstance(r, QualifiedRule)]
    assert len(qualified_rules) == 0


def test_15_complex_values_calc_and_url():
    """Case 15: Declarations with complex values like calc() with nesting and url() with paths."""
    css = """
    .banner {
        width: calc(100vw - (2 * 16px));
        background-image: url("https://cdn.example.com/assets/images/hero banner (1).png");
        clip-path: polygon(0 0, 100% 0, 100% calc(100% - 40px), 0 100%);
    }
    """
    parsed = parse_css(css)
    assert len(parsed.rules) == 1
    rule = parsed.rules[0]
    assert isinstance(rule, QualifiedRule)
    decls = {d.property: d.value for d in rule.declarations}

    assert decls["width"] == "calc(100vw - (2 * 16px))"
    assert decls["background-image"] == 'url("https://cdn.example.com/assets/images/hero banner (1).png")'
    assert decls["clip-path"] == "polygon(0 0, 100% 0, 100% calc(100% - 40px), 0 100%)"


def test_invalid_path_is_directory(tmp_path: Path):
    """Verify specifying a directory path raises InvalidCSSFileError."""
    test_dir = tmp_path / "somedir"
    test_dir.mkdir()
    with pytest.raises(InvalidCSSFileError):
        parse_css_file(test_dir)
