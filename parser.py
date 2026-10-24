"""
CSS Parser Module using tinycss2.

Responsible for tokenizing CSS stylesheets, extracting qualified rules,
at-rules (@media, @supports, @keyframes, @font-face, etc.), and declarations
with full preservation of complex CSS values (calc, urls, commas, quotes).
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, List, Optional, Union

import tinycss2
from tinycss2.ast import AtRule as TinyAtRule
from tinycss2.ast import Declaration as TinyDeclaration
from tinycss2.ast import ParseError as TinyParseError
from tinycss2.ast import QualifiedRule as TinyQualifiedRule


# ============================================================================
# Exceptions
# ============================================================================

class CSSParserError(Exception):
    """Base exception for all CSS parser errors."""
    pass


class CSSFileNotFoundError(CSSParserError):
    """Raised when the specified CSS input file cannot be found."""
    pass


class EmptyFileError(CSSParserError):
    """Raised when the input CSS file is empty."""
    pass


class InvalidCSSFileError(CSSParserError):
    """Raised when the input file cannot be read or is invalid."""
    pass


# ============================================================================
# Data Models
# ============================================================================

@dataclass
class Diagnostic:
    """Represents a parsing error or warning diagnostic."""
    level: str  # 'error' or 'warning'
    message: str
    line: Optional[int] = None
    column: Optional[int] = None

    def to_dict(self) -> dict[str, Any]:
        """Convert diagnostic to dictionary representation."""
        data: dict[str, Any] = {
            "level": self.level,
            "message": self.message,
        }
        if self.line is not None:
            data["line"] = self.line
        if self.column is not None:
            data["column"] = self.column
        return data


@dataclass
class Declaration:
    """Represents an individual CSS property declaration."""
    property: str
    value: str
    important: bool = False

    def to_dict(self) -> dict[str, Any]:
        """Convert declaration to dictionary representation."""
        return {
            "property": self.property,
            "value": self.value,
            "important": self.important,
        }


@dataclass
class QualifiedRule:
    """Represents a standard CSS rule block (selector + declarations)."""
    selector: str
    selectors: list[str]
    declarations: list[Declaration] = field(default_factory=list)
    type: str = "qualified_rule"

    @property
    def declaration_count(self) -> int:
        """Return the number of declarations in this rule."""
        return len(self.declarations)

    def to_dict(self) -> dict[str, Any]:
        """Convert qualified rule to dictionary matching standard schema."""
        return {
            "type": self.type,
            "selector": self.selector,
            "declaration_count": self.declaration_count,
            "declarations": [d.to_dict() for d in self.declarations],
        }


@dataclass
class KeyframeRule:
    """Represents an individual keyframe block (e.g. from, 50%, to)."""
    selector: str
    declarations: list[Declaration] = field(default_factory=list)
    type: str = "keyframe_rule"

    @property
    def declaration_count(self) -> int:
        """Return the number of declarations in this keyframe block."""
        return len(self.declarations)

    def to_dict(self) -> dict[str, Any]:
        """Convert keyframe rule to dictionary."""
        return {
            "type": self.type,
            "selector": self.selector,
            "declaration_count": self.declaration_count,
            "declarations": [d.to_dict() for d in self.declarations],
        }


@dataclass
class AtRule:
    """Represents a CSS at-rule (@media, @keyframes, @font-face, etc.)."""
    at_keyword: str
    prelude: str
    rules: list[Union[QualifiedRule, AtRule, KeyframeRule]] = field(default_factory=list)
    declarations: list[Declaration] = field(default_factory=list)
    type: str = "at_rule"

    def to_dict(self) -> dict[str, Any]:
        """Convert at-rule to dictionary representation."""
        result: dict[str, Any] = {
            "type": self.type,
            "at_keyword": self.at_keyword,
            "prelude": self.prelude,
        }
        if self.rules:
            result["rules"] = [r.to_dict() for r in self.rules]
        if self.declarations:
            result["declaration_count"] = len(self.declarations)
            result["declarations"] = [d.to_dict() for d in self.declarations]
        return result


@dataclass
class ParsedStylesheet:
    """Represents the complete parsed stylesheet AST and metadata."""
    source: str
    rules: list[Union[QualifiedRule, AtRule, KeyframeRule]] = field(default_factory=list)
    diagnostics: list[Diagnostic] = field(default_factory=list)
    comments_count: int = 0


# ============================================================================
# Parser Implementation
# ============================================================================

class CSSParser:
    """Intelligent CSS parser built on top of tinycss2."""

    def __init__(self) -> None:
        self.diagnostics: list[Diagnostic] = []
        self.comments_count: int = 0

    def parse_string(self, css_text: str, source: str = "<string>") -> ParsedStylesheet:
        """
        Parse raw CSS text into a structured ParsedStylesheet object.

        Args:
            css_text: Raw CSS content to parse.
            source: Source identifier (e.g. filename).

        Returns:
            ParsedStylesheet containing parsed rules, diagnostics, and counts.
        """
        self.diagnostics = []
        self.comments_count = 0

        # Parse top-level stylesheet nodes, preserving comments for metrics
        top_nodes = tinycss2.parse_stylesheet(
            css_text,
            skip_comments=False,
            skip_whitespace=True,
        )

        rules: list[Union[QualifiedRule, AtRule, KeyframeRule]] = []
        for node in top_nodes:
            parsed_node = self._parse_top_level_node(node)
            if parsed_node is not None:
                rules.append(parsed_node)

        return ParsedStylesheet(
            source=source,
            rules=rules,
            diagnostics=self.diagnostics,
            comments_count=self.comments_count,
        )

    def parse_file(self, file_path: Union[str, Path]) -> ParsedStylesheet:
        """
        Read and parse a CSS file from disk.

        Args:
            file_path: Path to the CSS file.

        Returns:
            ParsedStylesheet object.

        Raises:
            CSSFileNotFoundError: If the file does not exist.
            InvalidCSSFileError: If the path is a directory or unreadable.
            EmptyFileError: If the file exists but has no content.
        """
        path = Path(file_path)

        if not path.exists():
            raise CSSFileNotFoundError(f"CSS file not found: '{file_path}'")

        if not path.is_file():
            raise InvalidCSSFileError(f"Specified path is not a regular file: '{file_path}'")

        try:
            content = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            try:
                # Fallback to latin-1 if UTF-8 fails
                content = path.read_text(encoding="latin-1")
            except Exception as e:
                raise InvalidCSSFileError(f"Failed to read file '{file_path}': {e}") from e
        except Exception as e:
            raise InvalidCSSFileError(f"Unable to read file '{file_path}': {e}") from e

        if not content.strip():
            raise EmptyFileError(f"Input CSS file is empty: '{file_path}'")

        return self.parse_string(content, source=path.name)

    # ------------------------------------------------------------------------
    # Internal Node Parsers
    # ------------------------------------------------------------------------

    def _parse_top_level_node(
        self, node: Any
    ) -> Optional[Union[QualifiedRule, AtRule, KeyframeRule]]:
        """Process a top-level AST node."""
        if node.type == "comment":
            self.comments_count += 1
            return None

        if node.type == "error":
            self.diagnostics.append(
                Diagnostic(
                    level="error",
                    message=f"Stylesheet syntax error: {node.message}",
                    line=getattr(node, "source_line", None),
                    column=getattr(node, "source_column", None),
                )
            )
            return None

        if node.type == "qualified-rule":
            return self._parse_qualified_rule(node)

        if node.type == "at-rule":
            return self._parse_at_rule(node)

        return None

    def _parse_qualified_rule(self, node: TinyQualifiedRule) -> QualifiedRule:
        """
        Parse a qualified rule into a QualifiedRule object.
        Preserves original selector string and extracts split selectors.
        """
        # Serialize selector prelude
        raw_selector = tinycss2.serialize(node.prelude).strip()
        # Clean multi-line whitespace while keeping selector combinators intact
        cleaned_selector = " ".join(
            line.strip() for line in raw_selector.splitlines() if line.strip()
        )
        # Fallback to raw if cleaned is somehow empty
        selector_str = cleaned_selector if cleaned_selector else raw_selector

        # Split individual selectors safely on top-level comma tokens
        individual_selectors = self._split_selectors_on_top_level_commas(node.prelude)

        declarations = self._parse_declarations(node.content)
        return QualifiedRule(
            selector=selector_str,
            selectors=individual_selectors,
            declarations=declarations,
        )

    def _parse_at_rule(self, node: TinyAtRule) -> AtRule:
        """
        Parse an at-rule (@media, @supports, @keyframes, @font-face, etc.).
        Handles nested rule blocks, keyframe selectors, and direct declarations.
        """
        at_keyword = node.at_keyword.lower() if node.at_keyword else ""
        prelude_str = tinycss2.serialize(node.prelude).strip()
        # Clean multi-line formatting in prelude
        cleaned_prelude = " ".join(
            line.strip() for line in prelude_str.splitlines() if line.strip()
        )
        prelude = cleaned_prelude if cleaned_prelude else prelude_str

        # If at-rule has no block (e.g. @charset, @import), return immediately
        if node.content is None:
            return AtRule(at_keyword=at_keyword, prelude=prelude)

        # 1. At-rules that define keyframes: (@keyframes, @-webkit-keyframes)
        if "keyframes" in at_keyword:
            nested_rules = self._parse_keyframe_blocks(node.content)
            return AtRule(
                at_keyword=at_keyword,
                prelude=prelude,
                rules=nested_rules,
            )

        # 2. At-rules that directly contain declarations: (@font-face, @page, @viewport)
        if at_keyword in {"font-face", "page", "viewport", "counter-style", "property"}:
            declarations = self._parse_declarations(node.content)
            return AtRule(
                at_keyword=at_keyword,
                prelude=prelude,
                declarations=declarations,
            )

        # 3. Conditional / grouping at-rules that contain nested rules: (@media, @supports, @layer, @document)
        nested_rules = self._parse_nested_rule_list(node.content)
        return AtRule(
            at_keyword=at_keyword,
            prelude=prelude,
            rules=nested_rules,
        )

    def _parse_nested_rule_list(
        self, tokens: list[Any]
    ) -> list[Union[QualifiedRule, AtRule, KeyframeRule]]:
        """Parse nested rules inside grouping at-rules like @media or @supports."""
        nested_nodes = tinycss2.parse_rule_list(
            tokens,
            skip_comments=False,
            skip_whitespace=True,
        )
        nested_rules: list[Union[QualifiedRule, AtRule, KeyframeRule]] = []
        for node in nested_nodes:
            if node.type == "comment":
                self.comments_count += 1
                continue
            if node.type == "error":
                self.diagnostics.append(
                    Diagnostic(
                        level="error",
                        message=f"Nested rule syntax error: {node.message}",
                        line=getattr(node, "source_line", None),
                        column=getattr(node, "source_column", None),
                    )
                )
                continue
            if node.type == "qualified-rule":
                nested_rules.append(self._parse_qualified_rule(node))
            elif node.type == "at-rule":
                nested_rules.append(self._parse_at_rule(node))
        return nested_rules

    def _parse_keyframe_blocks(self, tokens: list[Any]) -> list[Union[QualifiedRule, AtRule, KeyframeRule]]:
        """Parse keyframe blocks (e.g. from, 50%, to) inside @keyframes."""
        raw_blocks = tinycss2.parse_rule_list(
            tokens,
            skip_comments=False,
            skip_whitespace=True,
        )
        keyframe_rules: list[Union[QualifiedRule, AtRule, KeyframeRule]] = []
        for block in raw_blocks:
            if block.type == "comment":
                self.comments_count += 1
                continue
            if block.type == "error":
                self.diagnostics.append(
                    Diagnostic(
                        level="error",
                        message=f"Keyframe syntax error: {block.message}",
                        line=getattr(block, "source_line", None),
                        column=getattr(block, "source_column", None),
                    )
                )
                continue
            if block.type == "qualified-rule":
                keyframe_selector = tinycss2.serialize(block.prelude).strip()
                decls = self._parse_declarations(block.content)
                keyframe_rules.append(
                    KeyframeRule(
                        selector=keyframe_selector,
                        declarations=decls,
                    )
                )
        return keyframe_rules

    def _parse_declarations(self, tokens: list[Any]) -> list[Declaration]:
        """
        Parse declaration list tokens into clean Declaration objects.
        Accurately preserves complex values, functions, commas, and !important.
        """
        raw_declarations = tinycss2.parse_declaration_list(
            tokens,
            skip_comments=False,
            skip_whitespace=True,
        )
        declarations: list[Declaration] = []

        for item in raw_declarations:
            if item.type == "comment":
                self.comments_count += 1
                continue

            if item.type == "error":
                self.diagnostics.append(
                    Diagnostic(
                        level="warning",
                        message=f"Malformed declaration: {item.message}",
                        line=getattr(item, "source_line", None),
                        column=getattr(item, "source_column", None),
                    )
                )
                continue

            if item.type == "declaration":
                prop_name = item.name
                # Normalize standard properties to lowercase, keep custom variables as-is
                if not prop_name.startswith("--"):
                    prop_name = prop_name.lower()

                # Cleanly serialize value preserving tokens
                value_str = tinycss2.serialize(item.value).strip()
                declarations.append(
                    Declaration(
                        property=prop_name,
                        value=value_str,
                        important=item.important,
                    )
                )

        return declarations

    def _split_selectors_on_top_level_commas(self, tokens: list[Any]) -> list[str]:
        """
        Split selector tokens on top-level comma literals only.
        Correctly avoids splitting commas inside function tokens like :is() or
        strings within attribute selectors like [data-attr="a,b"].
        """
        selectors: list[str] = []
        current_tokens: list[Any] = []

        for token in tokens:
            if token.type == "literal" and token.value == ",":
                part = tinycss2.serialize(current_tokens).strip()
                if part:
                    # Clean internal whitespace
                    cleaned = " ".join(line.strip() for line in part.splitlines() if line.strip())
                    selectors.append(cleaned if cleaned else part)
                current_tokens = []
            else:
                current_tokens.append(token)

        if current_tokens:
            part = tinycss2.serialize(current_tokens).strip()
            if part:
                cleaned = " ".join(line.strip() for line in part.splitlines() if line.strip())
                selectors.append(cleaned if cleaned else part)

        return selectors if selectors else [tinycss2.serialize(tokens).strip()]


# ============================================================================
# Public API Convenience Functions
# ============================================================================

def parse_css(css_text: str, source: str = "<string>") -> ParsedStylesheet:
    """Parse CSS text into a ParsedStylesheet."""
    parser = CSSParser()
    return parser.parse_string(css_text, source=source)


def parse_css_file(file_path: Union[str, Path]) -> ParsedStylesheet:
    """Read and parse a CSS file from disk into a ParsedStylesheet."""
    parser = CSSParser()
    return parser.parse_file(file_path)
