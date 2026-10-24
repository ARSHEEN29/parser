"""
CSS Analyzer Module.

Responsible for computing stylesheet statistics, property frequencies,
selector-property relationships, and validating aggregate metrics consistency.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
from typing import Any, Union

from parser import AtRule, KeyframeRule, ParsedStylesheet, QualifiedRule


@dataclass
class StylesheetSummary:
    """Statistical summary of a parsed stylesheet."""
    total_rules: int
    total_declarations: int
    unique_property_count: int
    unique_properties: list[str]
    property_frequency: dict[str, int]
    properties_by_selector: dict[str, list[str]]
    diagnostics_count: int
    comments_count: int

    def validate_consistency(self) -> bool:
        """
        Validate internal consistency of metrics:
        1. Unique properties count matches length of unique_properties list.
        2. Set of unique properties matches keys of property_frequency.
        3. Sum of all property frequencies equals total_declarations.
        """
        if len(self.unique_properties) != self.unique_property_count:
            return False
        if set(self.unique_properties) != set(self.property_frequency.keys()):
            return False
        if sum(self.property_frequency.values()) != self.total_declarations:
            return False
        return True

    def to_dict(self) -> dict[str, Any]:
        """Convert summary to dictionary representation."""
        return {
            "total_rules": self.total_rules,
            "total_declarations": self.total_declarations,
            "unique_property_count": self.unique_property_count,
            "unique_properties": self.unique_properties,
            "property_frequency": self.property_frequency,
            "properties_by_selector": self.properties_by_selector,
            "diagnostics_count": self.diagnostics_count,
            "comments_count": self.comments_count,
        }


class CSSAnalyzer:
    """Analyzes a ParsedStylesheet and extracts structured insights."""

    def analyze(self, parsed: ParsedStylesheet) -> StylesheetSummary:
        """
        Compute aggregate metrics from a ParsedStylesheet.

        Counting Policy:
        - total_rules: Counts all qualified styling rules and keyframe blocks
          across top-level and nested contexts (@media, @supports, @keyframes).
        - total_declarations: Counts every declaration parsed across all rules,
          including duplicate property declarations (order preserved).
        - property_frequency: Maps each property to its total occurrence count.
          The sum of frequencies strictly equals total_declarations.
        - unique_properties: Alphabetically sorted list of distinct property names.
        - properties_by_selector: Maps each selector to the list of properties
          declared on it across all matching rules.
        """
        total_rules = 0
        total_declarations = 0
        property_counter: Counter[str] = Counter()
        selector_properties: defaultdict[str, list[str]] = defaultdict(list)

        def process_rule(rule: Union[QualifiedRule, AtRule, KeyframeRule]) -> None:
            nonlocal total_rules, total_declarations

            if isinstance(rule, QualifiedRule):
                total_rules += 1
                props_in_rule = [d.property for d in rule.declarations]
                total_declarations += len(props_in_rule)
                for prop in props_in_rule:
                    property_counter[prop] += 1

                # Group by individual selectors if split, else rule selector
                target_selectors = rule.selectors if rule.selectors else [rule.selector]
                for sel in target_selectors:
                    selector_properties[sel].extend(props_in_rule)

            elif isinstance(rule, KeyframeRule):
                total_rules += 1
                props_in_rule = [d.property for d in rule.declarations]
                total_declarations += len(props_in_rule)
                for prop in props_in_rule:
                    property_counter[prop] += 1

                selector_properties[f"keyframe:{rule.selector}"].extend(props_in_rule)

            elif isinstance(rule, AtRule):
                # If at-rule contains direct declarations (@font-face, @page)
                if rule.declarations:
                    total_rules += 1
                    props_in_rule = [d.property for d in rule.declarations]
                    total_declarations += len(props_in_rule)
                    for prop in props_in_rule:
                        property_counter[prop] += 1

                    at_label = f"@{rule.at_keyword}" + (f" {rule.prelude}" if rule.prelude else "")
                    selector_properties[at_label].extend(props_in_rule)

                # Recursively process nested rules (@media, @supports, @keyframes)
                for child_rule in rule.rules:
                    process_rule(child_rule)

        for rule in parsed.rules:
            process_rule(rule)

        # Sort unique properties alphabetically
        unique_properties = sorted(property_counter.keys())

        # Sort property frequency by count descending, then alphabetical for determinism
        sorted_frequency = dict(
            sorted(property_counter.items(), key=lambda item: (-item[1], item[0]))
        )

        # Deterministic dictionary for selector properties
        sorted_selector_props = {
            sel: props for sel, props in sorted(selector_properties.items())
        }

        summary = StylesheetSummary(
            total_rules=total_rules,
            total_declarations=total_declarations,
            unique_property_count=len(unique_properties),
            unique_properties=unique_properties,
            property_frequency=sorted_frequency,
            properties_by_selector=sorted_selector_props,
            diagnostics_count=len(parsed.diagnostics),
            comments_count=parsed.comments_count,
        )

        assert summary.validate_consistency(), "Summary metrics failed internal consistency check!"
        return summary


def build_analysis_document(parsed: ParsedStylesheet) -> dict[str, Any]:
    """
    Build the final structured dictionary ready for JSON serialization.

    Matches schema:
    {
      "source": "...",
      "summary": { ... },
      "rules": [ ... ],
      "diagnostics": [ ... ]
    }
    """
    analyzer = CSSAnalyzer()
    summary = analyzer.analyze(parsed)

    return {
        "source": parsed.source,
        "summary": summary.to_dict(),
        "rules": [rule.to_dict() for rule in parsed.rules],
        "diagnostics": [diag.to_dict() for diag in parsed.diagnostics],
    }
