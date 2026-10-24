"""
Unit tests for CSSAnalyzer and summary metrics in analyzer.py.
Verifies counting consistency, property frequency calculations,
selector-property grouping, and schema conformity.
"""

import pytest

from analyzer import CSSAnalyzer, build_analysis_document
from parser import CSSParser, parse_css


def test_analyzer_basic_summary():
    """Verify basic summary calculations for simple rules."""
    css = """
    .card {
        color: red;
        font-size: 16px;
    }
    .button {
        color: blue;
        padding: 8px;
    }
    """
    parsed = parse_css(css, source="basic.css")
    analyzer = CSSAnalyzer()
    summary = analyzer.analyze(parsed)

    assert summary.total_rules == 2
    assert summary.total_declarations == 4
    assert summary.unique_property_count == 3
    assert summary.unique_properties == ["color", "font-size", "padding"]

    # Frequencies
    assert summary.property_frequency == {
        "color": 2,
        "font-size": 1,
        "padding": 1,
    }

    # Grouping by selector
    assert summary.properties_by_selector[".card"] == ["color", "font-size"]
    assert summary.properties_by_selector[".button"] == ["color", "padding"]

    assert summary.validate_consistency() is True


def test_analyzer_duplicate_declarations_counted_separately():
    """Verify duplicate declarations are counted separately and order preserved."""
    css = """
    .flexbox {
        display: -webkit-flex;
        display: flex;
        color: #111;
        color: #222;
        color: #333;
    }
    """
    parsed = parse_css(css)
    analyzer = CSSAnalyzer()
    summary = analyzer.analyze(parsed)

    # 1 rule, 5 total declarations
    assert summary.total_rules == 1
    assert summary.total_declarations == 5
    assert summary.unique_property_count == 2
    assert summary.unique_properties == ["color", "display"]

    assert summary.property_frequency["color"] == 3
    assert summary.property_frequency["display"] == 2

    # Selector contains all 5 declarations
    assert summary.properties_by_selector[".flexbox"] == [
        "display",
        "display",
        "color",
        "color",
        "color",
    ]
    assert summary.validate_consistency() is True


def test_analyzer_nested_media_and_keyframes_included():
    """Verify rules and declarations inside @media and @keyframes are counted in summary."""
    css = """
    .header {
        font-size: 20px;
    }

    @media (max-width: 600px) {
        .header {
            font-size: 16px;
        }
        .nav {
            display: none;
        }
    }

    @keyframes spin {
        from {
            transform: rotate(0deg);
        }
        to {
            transform: rotate(360deg);
        }
    }
    """
    parsed = parse_css(css)
    analyzer = CSSAnalyzer()
    summary = analyzer.analyze(parsed)

    # 1 top-level rule + 2 media rules + 2 keyframe rules = 5 total rules
    assert summary.total_rules == 5
    # 1 header + (1 header + 1 nav) + (1 from + 1 to) = 5 declarations
    assert summary.total_declarations == 5
    assert summary.unique_property_count == 3
    assert summary.unique_properties == ["display", "font-size", "transform"]

    assert summary.property_frequency["font-size"] == 2
    assert summary.property_frequency["transform"] == 2
    assert summary.property_frequency["display"] == 1

    # Properties by selector: .header defined in both top-level and media query
    assert summary.properties_by_selector[".header"] == ["font-size", "font-size"]
    assert summary.properties_by_selector["keyframe:from"] == ["transform"]
    assert summary.properties_by_selector["keyframe:to"] == ["transform"]

    assert summary.validate_consistency() is True


def test_analyzer_multi_selector_expansion():
    """Verify rules with multiple comma-separated selectors expand to all selectors."""
    css = """
    h1, h2, h3 {
        font-weight: 700;
        margin-top: 1em;
    }
    h1 {
        font-size: 32px;
    }
    """
    parsed = parse_css(css)
    analyzer = CSSAnalyzer()
    summary = analyzer.analyze(parsed)

    # 2 qualified rules
    assert summary.total_rules == 2
    assert summary.total_declarations == 3  # 2 in h1/h2/h3 + 1 in h1

    # In properties_by_selector, h1 received props from both rules
    assert summary.properties_by_selector["h1"] == ["font-weight", "margin-top", "font-size"]
    assert summary.properties_by_selector["h2"] == ["font-weight", "margin-top"]
    assert summary.properties_by_selector["h3"] == ["font-weight", "margin-top"]

    assert summary.validate_consistency() is True


def test_build_analysis_document_schema():
    """Verify build_analysis_document produces complete dictionary matching schema."""
    css = """
    /* Header comment */
    .card {
        color: red !important;
        width: 100px;
    }
    """
    parsed = parse_css(css, source="test.css")
    doc = build_analysis_document(parsed)

    # Required top-level keys
    assert "source" in doc
    assert "summary" in doc
    assert "rules" in doc
    assert "diagnostics" in doc

    assert doc["source"] == "test.css"
    summary = doc["summary"]
    assert summary["total_rules"] == 1
    assert summary["total_declarations"] == 2
    assert summary["unique_properties"] == ["color", "width"]
    assert summary["comments_count"] == 1

    rules = doc["rules"]
    assert len(rules) == 1
    assert rules[0]["selector"] == ".card"
    assert rules[0]["declaration_count"] == 2
    assert rules[0]["declarations"][0]["property"] == "color"
    assert rules[0]["declarations"][0]["value"] == "red"
    assert rules[0]["declarations"][0]["important"] is True


def test_analyzer_empty_stylesheet_summary():
    """Verify summary metrics on a stylesheet with 0 rules."""
    css = "/* Only a comment */"
    parsed = parse_css(css, source="empty.css")
    analyzer = CSSAnalyzer()
    summary = analyzer.analyze(parsed)

    assert summary.total_rules == 0
    assert summary.total_declarations == 0
    assert summary.unique_property_count == 0
    assert summary.unique_properties == []
    assert summary.property_frequency == {}
    assert summary.properties_by_selector == {}
    assert summary.comments_count == 1
    assert summary.validate_consistency() is True
