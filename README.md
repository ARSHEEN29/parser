# CSS Intelligent Parser — Skill First Labs Milestone 1

A production-quality, deterministic command-line interface (CLI) tool and Python library for parsing CSS stylesheets into structured, machine-readable JSON data.

Built for the **Skill First Labs Milestone 1** technical evaluation.

---

## 1. Project Overview

The **CSS Intelligent Parser** reads CSS stylesheets and extracts semantic, structured information rather than dumping raw text. It parses CSS syntax into a clean Abstract Syntax Tree (AST), identifies rules and at-rules (`@media`, `@keyframes`, `@font-face`), extracts property declarations and values, flags `!important` rules, and computes comprehensive stylesheet metrics.

### Key Capabilities
- **Token-Aware CSS3 Parsing**: Powered by `tinycss2`, adhering to W3C CSS Syntax Level 3.
- **Complex Value Preservation**: Accurately preserves functions (`calc()`, `var()`, `linear-gradient()`), colors (`rgb()`, `rgba()`, `#hex`), quoted font stacks, and URLs without naive string splitting.
- **Advanced At-Rule Support**: Recursively parses nested `@media` queries and `@keyframes` animation blocks (`from`, `to`, percentage selectors).
- **Vendor Prefix & Cascade Preservation**: Retains duplicate declarations in source order.
- **Stylesheet Analytics**: Computes rule counts, declaration totals, unique properties, property frequency distributions, and selector-property mappings.
- **Resilient Error Recovery**: Transparently collects diagnostics for malformed syntax without crashing.

---

## 2. Problem Statement

Raw CSS is unstructured text. Downstream developer tools—such as design system auditors, style linters, dead-code elimination pipelines, and migration scripts—require structured data to reason about stylesheets.

Naive approaches relying on regular expressions or simple string splitting (`split(';')`, `split(':')`, `split(',')`) frequently fail when handling:
1. Nested blocks (e.g. `@media`, `@keyframes`, `@supports`).
2. Semicolons and colons inside quoted strings or URLs (e.g. `content: "Warning: Alert;";` or `url("https://example.com/asset.png")`).
3. Commas inside function values (e.g. `rgb(255, 0, 0)`, `0 10px 20px rgba(0, 0, 0, 0.2)`).
4. Commas inside pseudo-classes (e.g. `:is(.btn, .link)`).

An intelligent parser parses CSS grammar hierarchically, preserving valid tokens while structuring the result into predictable JSON.

---

## 3. Architecture and Module Responsibilities

The codebase follows a clean, decoupled architecture:

```
css-intelligent-parser/
├── main.py                     # CLI orchestration, argument parsing, exit codes
├── parser.py                   # Tokenization, AST extraction, tinycss2 adapter
├── analyzer.py                 # Summary metrics, property frequencies, selector mapping
├── requirements.txt            # Project dependencies (tinycss2, pytest)
├── README.md                   # Full documentation & demonstration guide
├── .gitignore                  # Git ignore rules for Python environments
├── sample.css                  # Demonstration stylesheet featuring all edge cases
├── tests/
│   ├── __init__.py
│   ├── test_parser.py          # 15 edge-case & parsing unit tests
│   ├── test_analyzer.py        # Analytics, consistency, and schema tests
│   └── test_cli.py             # CLI commands, arguments, and exit code tests
└── examples/
    └── expected_output.json    # Pre-generated JSON output for sample.css
```

### Module Responsibilities

- **`parser.py`**:
  - Direct interface with `tinycss2`.
  - Converts CSS text into strongly typed dataclasses (`QualifiedRule`, `AtRule`, `KeyframeRule`, `Declaration`, `Diagnostic`, `ParsedStylesheet`).
  - Safely tokenizes selectors by splitting top-level comma literals only.
  - Distinguishes fatal file errors (`CSSFileNotFoundError`, `EmptyFileError`, `InvalidCSSFileError`) from recoverable syntax diagnostics.

- **`analyzer.py`**:
  - Consumes a `ParsedStylesheet` and calculates aggregate metrics.
  - Computes `total_rules`, `total_declarations`, `unique_properties`, `property_frequency`, and `properties_by_selector`.
  - Strictly asserts internal consistency:
    $$\sum \text{property\_frequency} = \text{total\_declarations}$$
  - Converts AST structures into standard serializable JSON dictionaries.

- **`main.py`**:
  - Implements the CLI using `argparse`.
  - Validates input paths, file existence, read permissions, file extensions, and non-empty content.
  - Formats output JSON (indented or compact).
  - Handles writing to stdout or to a specified `--output` file.
  - Returns exit code `0` on success and `1` on fatal errors.

---

## 4. Design Decisions

> **Evaluation Explanation — Design Choices:**
> We selected `tinycss2` over regular expressions because regex cannot reliably parse nested CSS grammar, quoted strings, or nested function parentheses. Outputting structured JSON provides a deterministic, standardized format easily consumable by linters, build systems, and design tooling. Separating parsing, analysis, and CLI concerns adheres to the Single Responsibility Principle, ensuring testability, maintainability, and reusability.

### Counting & Aggregation Policy
- **Qualified Rules**: `total_rules` counts every styling rule block, including top-level qualified rules, nested rules inside `@media` / `@supports`, and keyframe blocks (`from`, `to`, `50%`). Top-level container at-rules (like `@media`) are preserved in the rule tree without inflating the styling rule count.
- **Duplicate Declarations**: Counted individually in both `total_declarations` and `property_frequency`. In CSS, duplicate properties (such as vendor fallback chains like `display: -webkit-flex; display: flex;`) represent distinct declarations critical for browser compatibility.
- **Selector Mapping**: Multi-selector rules (e.g. `.card, #main-card`) index declared properties under both individual selectors, answering queries like "Which properties apply to `.card` across the entire stylesheet?".

---

## 5. Documented Edge Case: Complex Values & Delimiters

> **Evaluation Explanation — Documented Edge Case:**
> Consider a CSS declaration with complex delimiters:
> ```css
> box-shadow: 0 10px 20px rgba(0, 0, 0, 0.2);
> font-family: "Helvetica Neue", Arial, sans-serif;
> width: calc(100% - 20px);
> ```
> Naive parsers splitting on commas or spaces corrupt these values into fragmented, invalid strings (e.g. splitting `rgba(0` and `0` and `0.2)`).
>
> **How our parser handles this:** `tinycss2` tokenizes `rgba(...)` and `calc(...)` into discrete `FunctionToken` objects containing nested arguments, and `"Helvetica Neue"` into a `StringToken`. The parser serializes the declaration value directly from the token stream (`tinycss2.serialize(decl.value)`). Because function contents and string literals are protected tokens in the AST, internal commas and spaces remain intact as a unified value: `"0 10px 20px rgba(0, 0, 0, 0.2)"`.

---

## 6. Installation & Setup

### Prerequisites
- Python 3.11 or higher (tested on Python 3.14 on Windows 11).
- PowerShell / Command Prompt / Bash.

### Setup Instructions (Windows PowerShell)

```powershell
# 1. Clone the repository
git clone https://github.com/YOUR_USERNAME/css-intelligent-parser.git
cd css-intelligent-parser

# 2. (Optional) Create and activate a virtual environment
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# 3. Install required dependencies
pip install -r requirements.txt
```

---

## 7. How to Run the Parser

### Basic Usage (Output to stdout)

```powershell
python main.py sample.css
```

### Save Output to a JSON File

```powershell
python main.py sample.css --output output.json
# Or using the short flag:
python main.py sample.css -o output.json
```

### Output Formatting Options

```powershell
# Minified single-line JSON
python main.py sample.css --compact

# Custom indentation (e.g. 4 spaces)
python main.py sample.css --indent 4
```

### CLI Options Summary

| Argument | Flag | Description | Default |
|---|---|---|---|
| `input_file` | Positional | Path to the input `.css` file | *Required* |
| `--output` | `-o` | File path to write the output JSON | `stdout` |
| `--indent` | N/A | Number of spaces for JSON indentation | `2` |
| `--compact` | N/A | Minify JSON output onto a single line | `False` |
| `--version` | `-v` | Display parser version | N/A |
| `--help` | `-h` | Display usage and options | N/A |

---

## 8. JSON Output Schema

The parser produces clean, deterministic JSON structured as follows:

```json
{
  "source": "sample.css",
  "summary": {
    "total_rules": 9,
    "total_declarations": 29,
    "unique_property_count": 18,
    "unique_properties": [
      "--accent-color",
      "--font-stack",
      "--primary-color",
      "--spacing-unit",
      "background-color",
      "background-image",
      "box-shadow",
      "color",
      "display",
      "flex-direction",
      "font-display",
      "font-family",
      "margin",
      "opacity",
      "padding",
      "src",
      "transform",
      "width"
    ],
    "property_frequency": {
      "display": 3,
      "opacity": 3,
      "background-color": 2,
      "box-shadow": 2,
      "color": 2,
      "font-family": 2,
      "margin": 2,
      "transform": 2,
      "width": 2,
      "--accent-color": 1,
      "--font-stack": 1,
      "--primary-color": 1,
      "--spacing-unit": 1,
      "background-image": 1,
      "flex-direction": 1,
      "font-display": 1,
      "padding": 1,
      "src": 1
    },
    "properties_by_selector": {
      ".card": [
        "display",
        "display",
        "flex-direction",
        "margin",
        "padding",
        "color",
        "background-color",
        "background-image",
        "font-family",
        "box-shadow",
        "width",
        "margin",
        "width",
        "box-shadow"
      ]
    },
    "diagnostics_count": 0,
    "comments_count": 7
  },
  "rules": [
    {
      "type": "qualified_rule",
      "selector": ".card, .panel, #featured-card",
      "declaration_count": 11,
      "declarations": [
        {
          "property": "display",
          "value": "-webkit-box",
          "important": false
        },
        {
          "property": "display",
          "value": "flex",
          "important": false
        },
        {
          "property": "color",
          "value": "#2c3e50",
          "important": true
        },
        {
          "property": "box-shadow",
          "value": "0 10px 20px rgba(0, 0, 0, 0.15)",
          "important": false
        },
        {
          "property": "width",
          "value": "calc(100% - 20px)",
          "important": false
        }
      ]
    },
    {
      "type": "at_rule",
      "at_keyword": "media",
      "prelude": "(max-width: 768px)",
      "rules": [
        {
          "type": "qualified_rule",
          "selector": ".card, .panel",
          "declaration_count": 3,
          "declarations": [
            {
              "property": "margin",
              "value": "5px 10px",
              "important": false
            }
          ]
        }
      ]
    },
    {
      "type": "at_rule",
      "at_keyword": "keyframes",
      "prelude": "slidein",
      "rules": [
        {
          "type": "keyframe_rule",
          "selector": "from",
          "declaration_count": 2,
          "declarations": [
            {
              "property": "transform",
              "value": "translateX(-100%)",
              "important": false
            }
          ]
        }
      ]
    }
  ],
  "diagnostics": []
}
```

A complete reference file is provided in [`examples/expected_output.json`](examples/expected_output.json).

---

## 9. Automated Testing & Verification

The project includes an automated test suite implemented with `pytest`.

### Running Tests

```powershell
pytest -v
```

### Test Coverage Breakdown (29 Total Tests)

1. **Parser Tests (`tests/test_parser.py`) — 16 Tests**:
   - `test_1_normal_css_multiple_rules`: Multiple qualified rules and declarations.
   - `test_2_empty_file`: Rejection of 0-byte and whitespace-only files with `EmptyFileError`.
   - `test_3_comments_only_file`: Comments-only stylesheet parsed without crashing.
   - `test_4_multiple_selectors_in_one_rule`: Preserves combined selector and split selectors.
   - `test_5_duplicate_declarations`: Order and presence of duplicate declarations.
   - `test_6_important_declarations`: Accurate identification of `!important`.
   - `test_7_values_containing_commas_and_parentheses`: Values with `rgb()`, `rgba()`, `linear-gradient()`.
   - `test_8_quoted_strings_containing_punctuation`: Font stacks and `content` properties with punctuation.
   - `test_9_css_custom_properties`: CSS variables (`--primary-color`) with casing preserved.
   - `test_10_nested_media_rules`: Nested rules inside `@media` queries.
   - `test_11_keyframes_selectors`: Keyframe stages (`from`, `50%`, `to`).
   - `test_12_malformed_css_recovery`: Non-fatal diagnostic recovery from malformed CSS.
   - `test_13_missing_input_file`: Verification that missing file raises `CSSFileNotFoundError`.
   - `test_14_input_with_no_qualified_css_rules`: Stylesheets containing only at-rules (e.g. `@charset`, `@import`).
   - `test_15_complex_values_calc_and_url`: Nested `calc()` and URL strings containing spaces and parentheses.
   - `test_invalid_path_is_directory`: Rejection of directory paths with `InvalidCSSFileError`.

2. **Analyzer Tests (`tests/test_analyzer.py`) — 6 Tests**:
   - `test_analyzer_basic_summary`: Metric counts on standard stylesheet.
   - `test_analyzer_duplicate_declarations_counted_separately`: Consistency across duplicate declarations.
   - `test_analyzer_nested_media_and_keyframes_included`: Nested rule metrics.
   - `test_analyzer_multi_selector_expansion`: Associating properties with all selectors in multi-selector rules.
   - `test_build_analysis_document_schema`: Complete JSON dictionary structure and types.
   - `test_analyzer_empty_stylesheet_summary`: Metrics on 0-rule stylesheets.

3. **CLI Tests (`tests/test_cli.py`) — 7 Tests**:
   - `test_cli_stdout_success`: Emitting JSON to standard output.
   - `test_cli_output_file_argument`: Writing JSON to an explicit file path.
   - `test_cli_compact_flag`: Minified JSON emission on 1 line.
   - `test_cli_missing_file_error`: Exit code `1` and error message for missing files.
   - `test_cli_empty_file_error`: Exit code `1` and error message for empty files.
   - `test_cli_directory_path_error`: Exit code `1` when passing a directory.
   - `test_cli_non_css_extension_warning`: Warning message emitted when file lacks `.css` extension.

---

## 10. Known Limitations

To remain lightweight, robust, and self-contained:
1. **No Network Resolution**: The parser does not fetch or download external stylesheets referenced in `@import url(...)`.
2. **No CSS Specificity Calculator**: The parser reports selectors exactly as authored but does not rank them by CSS specificity weight (e.g., `(0, 1, 0)`).
3. **No Layout Engine / Cascade Resolution**: The parser does not compute final computed values (e.g., resolving `1rem` to `16px` or resolving browser inheritance).

---

## 11. Demonstration Plan (Technical Evaluation Video)

Follow this 2-minute walkthrough when recording a demonstration:

1. **Terminal Setup (15s)**:
   - Display the project directory layout:
     ```powershell
     Get-ChildItem -Name
     ```
2. **Execute Automated Tests (30s)**:
   - Run the test suite to verify 100% pass rate:
     ```powershell
     pytest -v
     ```
3. **Run CLI with Sample CSS (30s)**:
   - Parse `sample.css` to stdout and demonstrate the structured JSON:
     ```powershell
     python main.py sample.css
     ```
   - Export to a file:
     ```powershell
     python main.py sample.css --output output.json
     ```
4. **Highlight Edge Cases in Output (30s)**:
   - Open `output.json` and highlight:
     - Preserved `calc(100% - 20px)` and `url("images/background image.png")`.
     - `!important` flag set to `true`.
     - Duplicate `display: -webkit-box; display: flex;` preserved in sequence.
     - Nested `@media` and `@keyframes` rules.
5. **Demonstrate Error Handling (15s)**:
   - Demonstrate the clean error message on a missing file:
     ```powershell
     python main.py missing.css
     Write-Output "Exit code: $LASTEXITCODE"
     ```



# Add your GitHub repository remote
git remote add origin https://github.com/YOUR_USERNAME/css-intelligent-parser.git

# Push to GitHub
git push -u origin main
```
