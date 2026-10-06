"""Streamlit Frontend for Phase 1 Software Application Name Normalizer."""

import io
import time
from typing import List
import pandas as pd
import streamlit as st

from app.normalizer import NameNormalizer


# -----------------------------------------------------------------------------
# Page Configuration & Modern Styling
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="Software Name Normalizer | Phase 1",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
    /* Modern sleek styling */
    .main-header {
        font-size: 2.2rem;
        font-weight: 700;
        background: linear-gradient(90deg, #1E88E5, #7E57C2);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.2rem;
    }
    .sub-header {
        color: #616161;
        font-size: 1.05rem;
        margin-bottom: 1.5rem;
    }
    .metric-card {
        background: #F8FAFC;
        border: 1px solid #E2E8F0;
        border-radius: 10px;
        padding: 1rem;
        text-align: center;
    }
    .metric-value {
        font-size: 1.8rem;
        font-weight: 700;
        color: #1E293B;
    }
    .metric-label {
        font-size: 0.85rem;
        color: #64748B;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }
    .badge-changed {
        background-color: #E0F2FE;
        color: #0369A1;
        padding: 3px 8px;
        border-radius: 4px;
        font-weight: 600;
        font-size: 0.8rem;
    }
    .badge-kept {
        background-color: #F1F5F9;
        color: #475569;
        padding: 3px 8px;
        border-radius: 4px;
        font-size: 0.8rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# -----------------------------------------------------------------------------
# Initialize Normalizer (Phase 1 Pure Deterministic Mode)
# -----------------------------------------------------------------------------
@st.cache_resource
def get_normalizer() -> NameNormalizer:
    """Load Phase 1 deterministic engine without search, crawler, or LLM overhead."""
    return NameNormalizer(use_cache=False, use_fuzzy=False, enable_semantic=False)


normalizer = get_normalizer()


# -----------------------------------------------------------------------------
# Sidebar: Phase 1 Rules Reference
# -----------------------------------------------------------------------------
with st.sidebar:
    st.image("https://img.icons8.com/fluency/96/clean.png", width=64)
    st.title("Engine Config")
    st.markdown("**Phase 1 Deterministic Engine**")
    st.info(
        "Strictly conservative software product canonical name resolver. "
        "Operates 100% offline with zero hallucinations."
    )

    st.markdown("### Supported Normalizations")
    with st.expander("🖥️ OS & Platforms in Parentheses", expanded=True):
        st.markdown(
            """
            Removes platform metadata inside `(...)`:
            - `(HP-UX)`
            - `(Android)`
            - `(Linux)`
            - `(Windows)`
            - `(macOS)` / `(Mac)`
            - `(AIX)`
            - `(Solaris)`
            - `(NL)` *(Netherlands/Localization)*
            - `for Windows`, `for Mac`, etc.
            
            *Legitimate product parentheses (e.g. `AutoCAD (LT)`) and platforms (e.g. `for SAP R/3`) are preserved.*
            """
        )

    with st.expander("🏷️ Prefixes & Licensing Terms", expanded=True):
        st.markdown(
            """
            - `TS-` inventory prefixes
            - Licensing / deployment metadata:
              - `Enterprise`, `Professional`, `Standard`
              - `Non-Production Environment`, `QA`, `UAT`, `NEBS`
              - `Network License`, `Standalone License`
            - Bracket metadata:
              - Removes everything from last bracket to end: `(reg)`, `(Trial)`, `(QA)`
            """
        )

    with st.expander("📅 Versions, Releases & Years"):
        st.markdown(
            """
            - Trailing & dotted versions stripped: `11`, `6.5`, `0.3`
            - Release numbers stripped: `R2`, `SP1`, `Release 4`
            - Release years stripped: `2011`, `2018`, `2022`
            - Hardware models & official identifiers preserved: `Citrix ADC MPX 14500`, `Microsoft 365`
            """
        )


# -----------------------------------------------------------------------------
# Main Application Content
# -----------------------------------------------------------------------------
st.markdown('<div class="main-header">Software Application Name Normalizer</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="sub-header">Clean messy software inventories into canonical product names using deterministic rules and web verification.</div>',
    unsafe_allow_html=True,
)

tab_batch, tab_single = st.tabs(["📁 Batch File Normalizer (CSV & Excel)", "🔍 Interactive Single Tester"])


# =============================================================================
# Tab 1: Batch File Normalizer (CSV & Excel)
# =============================================================================
with tab_batch:
    st.markdown("Upload a CSV or Excel spreadsheet (`.xlsx`, `.xls`) containing software application names to normalize in batch.")

    uploaded_file = st.file_uploader(
        "Choose a CSV or Excel file",
        type=["csv", "xlsx", "xls"],
        help="Upload CSV or Excel file with up to 5,000 records",
    )

    if uploaded_file is not None:
        try:
            is_excel = uploaded_file.name.lower().endswith((".xlsx", ".xls"))
            if is_excel:
                excel_obj = pd.ExcelFile(uploaded_file)
                if len(excel_obj.sheet_names) > 1:
                    selected_sheet = st.selectbox(
                        "📑 Select Excel Sheet:",
                        options=excel_obj.sheet_names,
                        index=0,
                    )
                    df = pd.read_excel(excel_obj, sheet_name=selected_sheet)
                else:
                    df = pd.read_excel(excel_obj, sheet_name=excel_obj.sheet_names[0])
            else:
                df = pd.read_csv(uploaded_file)

            total_file_rows = len(df)

            if total_file_rows == 0:
                st.warning("The uploaded file is empty.")
            else:
                # Column selection
                st.markdown("### 1. Select Column")
                columns = df.columns.tolist()

                # Default to 'Name' or 'Raw_Name' if available
                default_idx = 0
                for candidate_name in ["Name", "Raw_Name", "name", "raw_name", "Software", "Application"]:
                    if candidate_name in columns:
                        default_idx = columns.index(candidate_name)
                        break

                selected_col = st.selectbox(
                    "Column containing raw software names:",
                    options=columns,
                    index=default_idx,
                )

                # Limit to 5,000 names per feature requirement
                max_allowed = 5000
                if total_file_rows > max_allowed:
                    st.warning(
                        f"⚠️ Dataset contains **{total_file_rows:,}** rows. "
                        f"Processing the first **{max_allowed:,}** records for interactive responsiveness."
                    )
                    process_df = df.iloc[:max_allowed].copy()
                else:
                    process_df = df.copy()

                records_to_process = len(process_df)
                st.info(f"Ready to normalize **{records_to_process:,}** names from column **'{selected_col}'**.")

                # Action button
                if st.button("🚀 Normalize Dataset", type="primary", use_container_width=True):
                    progress_bar = st.progress(0, text="Initializing normalization...")
                    start_time = time.time()

                    raw_names = process_df[selected_col].fillna("").astype(str).tolist()
                    normalized_names: List[str] = []
                    rules_list: List[str] = []
                    changed_list: List[bool] = []

                    # Process names
                    chunk_size = max(1, records_to_process // 20)
                    for idx, raw in enumerate(raw_names):
                        res = normalizer.normalize_structured(raw)
                        normalized_names.append(res.normalized_name)
                        rules_list.append(", ".join(res.rules_applied) if res.rules_applied else "None")
                        changed_list.append(res.normalized_name != raw)

                        if (idx + 1) % chunk_size == 0 or idx == records_to_process - 1:
                            pct = int(((idx + 1) / records_to_process) * 100)
                            progress_bar.progress(pct, text=f"Normalized {idx + 1:,} / {records_to_process:,} names...")

                    elapsed = time.time() - start_time
                    progress_bar.empty()

                    # Attach normalized column per Section 19
                    process_df["Normalized_Application"] = normalized_names
                    process_df["Rules_Applied"] = rules_list
                    process_df["Changed"] = changed_list

                    changed_count = sum(changed_list)
                    unchanged_count = records_to_process - changed_count
                    rate = (changed_count / records_to_process) * 100 if records_to_process > 0 else 0

                    # Metrics display
                    st.markdown("### 2. Normalization Summary")
                    col1, col2, col3, col4, col5 = st.columns(5)
                    with col1:
                        st.metric("Total Processed", f"{records_to_process:,}")
                    with col2:
                        st.metric("Names Cleaned", f"{changed_count:,}", f"{rate:.1f}%")
                    with col3:
                        st.metric("Names Unchanged", f"{unchanged_count:,}")
                    with col4:
                        st.metric("Duration", f"{elapsed:.2f}s")
                    with col5:
                        speed = records_to_process / elapsed if elapsed > 0 else 0
                        st.metric("Throughput", f"{speed:,.0f}/sec")

                    # Results Table
                    st.markdown("### 3. Original Name ➔ Normalized Name Results")
                    
                    filter_choice = st.radio(
                        "Filter Results:",
                        ["All Records", "Cleaned / Changed Only", "Unchanged Only"],
                        horizontal=True,
                    )

                    view_df = process_df.copy()
                    if filter_choice == "Cleaned / Changed Only":
                        view_df = view_df[view_df["Changed"]]
                    elif filter_choice == "Unchanged Only":
                        view_df = view_df[~view_df["Changed"]]

                    # Display comparison view
                    display_cols = [selected_col, "Normalized_Application", "Rules_Applied", "Changed"]
                    st.dataframe(
                        view_df[display_cols].rename(
                            columns={
                                selected_col: "Original Name",
                                "Normalized_Application": "Normalized Name",
                                "Rules_Applied": "Rules Triggered",
                                "Changed": "Was Cleaned",
                            }
                        ),
                        use_container_width=True,
                        height=400,
                    )

                    # Download Options (CSV & Excel)
                    st.markdown("### 4. Download Results")
                    export_df = process_df.drop(columns=["Rules_Applied", "Changed"], errors="ignore")
                    
                    # Prepare CSV
                    csv_data = export_df.to_csv(index=False).encode("utf-8")
                    
                    # Prepare Excel
                    excel_buffer = io.BytesIO()
                    with pd.ExcelWriter(excel_buffer, engine="openpyxl") as writer:
                        export_df.to_excel(writer, index=False, sheet_name="Normalized Data")
                    excel_data = excel_buffer.getvalue()

                    base_filename = uploaded_file.name.rsplit(".", 1)[0]
                    down_col1, down_col2 = st.columns(2)
                    with down_col1:
                        st.download_button(
                            label="📥 Download Normalized CSV",
                            data=csv_data,
                            file_name=f"{base_filename}_normalized.csv",
                            mime="text/csv",
                            type="primary" if not is_excel else "secondary",
                            use_container_width=True,
                        )
                    with down_col2:
                        st.download_button(
                            label="📥 Download Normalized Excel (.xlsx)",
                            data=excel_data,
                            file_name=f"{base_filename}_normalized.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                            type="primary" if is_excel else "secondary",
                            use_container_width=True,
                        )

        except Exception as e:
            st.error(f"Error reading or processing file: {str(e)}")


# =============================================================================
# Tab 2: Interactive Single Tester
# =============================================================================
with tab_single:
    st.markdown("Test single application names interactively against the deterministic rules and web search verification.")

    example_names = [
        "TS-Altova DiffDog 2011 R2 Professional",
        "Veeam Backup & Replication 11 Enterprise",
        "IBM InfoSphere Information Server Pack 6.5 for SAP R/3 Non-Production Environment",
        "Solver SDK Platform 11",
        "ClaimMaster 2018 QA (reg)",
        "Citrix ADC MPX 14500 NEBS Enterprise",
        "BMC Performance Manager (HP-UX)",
        "AutoCAD (LT)",
        "Microsoft 365 Apps for enterprise",
    ]

    selected_example = st.selectbox("Or choose an example test case:", ["(Choose an example...)"] + example_names)

    default_value = selected_example if selected_example != "(Choose an example...)" else "TS-Altova DiffDog 2011 R2 Professional"
    
    col_inp, col_btn = st.columns([3, 1])
    with col_inp:
        test_input = st.text_input("Raw Application Name:", value=default_value)
    with col_btn:
        st.write("")
        st.write("")
        do_web_verify = st.button("🌐 Web Verify", help="Verify official canonical name using search and crawler")

    if test_input:
        if do_web_verify:
            with st.spinner("Executing multi-engine web search & authority crawl..."):
                from semantic.verifier import SemanticVerifier
                verifier = SemanticVerifier()
                res = verifier.verify(test_input)
        else:
            res = normalizer.normalize_structured(test_input)

        st.markdown("#### Normalization Result")
        res_col1, res_col2 = st.columns([1, 1])

        with res_col1:
            st.markdown(
                f"""
                <div style="background: #F1F5F9; border-radius: 8px; padding: 1rem;">
                    <div style="font-size: 0.8rem; color: #64748B; text-transform: uppercase;">Original Input</div>
                    <div style="font-size: 1.25rem; font-weight: 600; color: #334155; margin-top: 0.3rem;">{res.original_name}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        with res_col2:
            st.markdown(
                f"""
                <div style="background: #EFF6FF; border: 1px solid #BFDBFE; border-radius: 8px; padding: 1rem;">
                    <div style="font-size: 0.8rem; color: #2563EB; text-transform: uppercase;">Normalized Canonical Name</div>
                    <div style="font-size: 1.25rem; font-weight: 700; color: #1D4ED8; margin-top: 0.3rem;">{res.normalized_name}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        st.markdown("---")
        m_col1, m_col2, m_col3 = st.columns(3)
        with m_col1:
            st.metric("Confidence Score", f"{res.confidence:.2f}")
        with m_col2:
            status_text = "Cleaned" if res.changed else "Unchanged"
            st.metric("Status", status_text)
        with m_col3:
            st.metric("Resolution Method", res.method)

        if res.rules_applied:
            st.markdown("**Rules Triggered:**")
            st.write(", ".join([f"`{r}`" for r in res.rules_applied]))
        else:
            st.markdown("*No stripping rules triggered — name is already canonical or preserved.*")
