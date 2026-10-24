"""
Main CLI Module for the CSS Intelligent Parser.

Handles command-line arguments, orchestrates parsing and analysis,
formats output as clean deterministic JSON, and reports clear errors.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from analyzer import build_analysis_document
from parser import CSSFileNotFoundError, CSSParser, EmptyFileError, InvalidCSSFileError


def create_arg_parser() -> argparse.ArgumentParser:
    """Create and configure command-line argument parser."""
    parser = argparse.ArgumentParser(
        prog="css-parser",
        description="Skill First Labs CSS Intelligent Parser - Extract structured rules and insights from CSS stylesheets.",
    )
    parser.add_argument(
        "input_file",
        help="Path to the CSS file to parse.",
    )
    parser.add_argument(
        "-o",
        "--output",
        help="Optional path to write the output JSON file. If omitted, prints to stdout.",
        default=None,
    )
    parser.add_argument(
        "--indent",
        type=int,
        default=2,
        help="Indentation spaces for JSON output (default: 2).",
    )
    parser.add_argument(
        "--compact",
        action="store_true",
        help="Output minified single-line JSON without indentation.",
    )
    parser.add_argument(
        "-v",
        "--version",
        action="version",
        version="css-parser 1.0.0",
    )
    return parser


def run(argv: list[str] | None = None) -> int:
    """
    Main CLI entrypoint.

    Args:
        argv: List of command-line arguments (defaults to sys.argv[1:]).

    Returns:
        Exit status code: 0 on success, non-zero on error.
    """
    arg_parser = create_arg_parser()
    args = arg_parser.parse_args(argv)

    input_path = Path(args.input_file)

    # 1. Validate file extension (warn if not .css)
    if input_path.suffix.lower() != ".css":
        sys.stderr.write(
            f"Warning: '{input_path.name}' does not have a standard .css extension.\n"
        )

    # 2. Parse the CSS file
    parser = CSSParser()
    try:
        parsed_css = parser.parse_file(input_path)
    except CSSFileNotFoundError as err:
        sys.stderr.write(f"Error: {err}\n")
        return 1
    except EmptyFileError as err:
        sys.stderr.write(f"Error: {err}\n")
        return 1
    except InvalidCSSFileError as err:
        sys.stderr.write(f"Error: {err}\n")
        return 1
    except Exception as err:
        sys.stderr.write(f"Fatal error while parsing '{input_path}': {err}\n")
        return 1

    # 3. Build analysis document
    try:
        doc = build_analysis_document(parsed_css)
    except Exception as err:
        sys.stderr.write(f"Fatal error during stylesheet analysis: {err}\n")
        return 1

    # 4. Serialize to JSON
    indent = None if args.compact else args.indent
    try:
        json_output = json.dumps(doc, indent=indent, ensure_ascii=False)
    except Exception as err:
        sys.stderr.write(f"Failed to serialize output to JSON: {err}\n")
        return 1

    # 5. Output result
    if args.output:
        try:
            output_path = Path(args.output)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(json_output, encoding="utf-8")
            sys.stderr.write(
                f"Successfully parsed '{input_path.name}' -> '{args.output}' "
                f"({doc['summary']['total_rules']} rules, {doc['summary']['total_declarations']} declarations)\n"
            )
        except Exception as err:
            sys.stderr.write(f"Error writing output to '{args.output}': {err}\n")
            return 1
    else:
        sys.stdout.write(json_output + "\n")

    return 0


def main() -> None:
    """Entry point when executed as a script."""
    sys.exit(run())


if __name__ == "__main__":
    main()
