"""
Streamlit Web UI for CSS Intelligent Parser.

A clean, simple interactive dashboard for Skill First Labs Milestone 1.
Reads CSS input, extracts structured AST rules, displays metrics,
and renders clean tables and JSON.
"""

import json
from pathlib import Path
import streamlit as st
import pandas as pd

from analyzer import build_analysis_document
from parser import CSSParser, parse_css

# Page Configuration
st.set_page_config(
    page_title="CSS Intelligent Parser",
    page_icon="🎨",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Small, concise CSS example
SMALL_SAMPLE_CSS = """/* Simple Card Component */
.card {
    color: #2c3e50 !important;
    font-size: 16px;
    margin: 10px 20px;
    background-color: rgb(255, 255, 255);
    box-shadow: 0 10px 20px rgba(0, 0, 0, 0.2);
    width: calc(100% - 20px);
}

.card:hover {
    transform: translateY(-2px);
    color: #0070f3;
}
"""

# Header
st.title("🎨 CSS Intelligent Parser")
st.caption("Skill First Labs Milestone 1 • AST & Structured CSS Extraction")

# Sidebar - Example Presets & Upload
with st.sidebar:
    st.header("⚙️ Input Source")
    preset_choice = st.radio(
        "Choose an example preset:",
        ["Small Simple CSS", "Full sample.css", "Upload File / Custom"],
        index=0,
    )

    uploaded_file = None
    if preset_choice == "Upload File / Custom":
        uploaded_file = st.file_uploader("Upload a .css file", type=["css"])

# Determine default CSS text
if uploaded_file is not None:
    initial_css = uploaded_file.read().decode("utf-8")
    source_name = uploaded_file.name
elif preset_choice == "Full sample.css":
    sample_path = Path("sample.css")
    initial_css = sample_path.read_text(encoding="utf-8") if sample_path.exists() else SMALL_SAMPLE_CSS
    source_name = "sample.css"
else:
    initial_css = SMALL_SAMPLE_CSS
    source_name = "simple.css"

# Two-column layout
col_input, col_output = st.columns([1, 1], gap="large")

with col_input:
    st.subheader("📝 CSS Input")
    css_code = st.text_area(
        "Edit or paste CSS here:",
        value=initial_css,
        height=380,
        help="Type or paste CSS styles to parse into structured JSON.",
    )
    parse_button = st.button("🚀 Parse CSS", type="primary", use_container_width=True)

with col_output:
    st.subheader("📊 Structured Output")

    if not css_code.strip():
        st.warning("Please enter some CSS in the editor to parse.")
    else:
        try:
            # Parse using the core parser and analyzer modules
            parsed = parse_css(css_code, source=source_name)
            doc = build_analysis_document(parsed)
            summary = doc["summary"]

            # 1. Summary Metrics
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Total Rules", summary["total_rules"])
            m2.metric("Declarations", summary["total_declarations"])
            m3.metric("Unique Props", summary["unique_property_count"])
            m4.metric("Comments", summary["comments_count"])

            st.divider()

            # 2. Extracted Rules
            st.markdown("### 📋 Extracted Rules & Declarations")
            rules = doc.get("rules", [])
            if not rules:
                st.info("No rules found in CSS.")
            else:
                for idx, r in enumerate(rules, 1):
                    rule_type = r.get("type", "qualified_rule")
                    selector = r.get("selector") or f"@{r.get('at_keyword')} {r.get('prelude', '')}"
                    decl_count = r.get("declaration_count", 0)

                    with st.expander(f"**Rule {idx}:** `{selector}` ({decl_count} declarations)", expanded=(idx == 1)):
                        # If direct declarations exist
                        if r.get("declarations"):
                            rows = []
                            for d in r["declarations"]:
                                rows.append({
                                    "Property": d["property"],
                                    "Value": d["value"],
                                    "!important": "✅ Yes" if d.get("important") else "No"
                                })
                            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

                        # If nested rules exist (@media, @keyframes)
                        if r.get("rules"):
                            st.caption("Nested Rules:")
                            for child in r["rules"]:
                                child_sel = child.get("selector", "")
                                st.markdown(f"- **`{child_sel}`**")
                                if child.get("declarations"):
                                    child_rows = [{
                                        "Property": d["property"],
                                        "Value": d["value"],
                                        "!important": "✅ Yes" if d.get("important") else "No"
                                    } for d in child["declarations"]]
                                    st.dataframe(pd.DataFrame(child_rows), use_container_width=True, hide_index=True)

            # 3. Property Frequency Distribution
            st.divider()
            st.markdown("### 📈 Property Frequency")
            freq = summary.get("property_frequency", {})
            if freq:
                df_freq = pd.DataFrame(list(freq.items()), columns=["Property", "Count"]).set_index("Property")
                st.bar_chart(df_freq, height=220)

            # 4. JSON Output & Download
            st.divider()
            st.markdown("### 📄 Raw JSON Output")
            json_str = json.dumps(doc, indent=2)
            st.download_button(
                label="💾 Download JSON",
                data=json_str,
                file_name=f"{source_name}_output.json",
                mime="application/json",
            )
            st.json(doc, expanded=False)

        except Exception as e:
            st.error(f"Error parsing CSS: {e}")
