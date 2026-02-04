import streamlit as st
import json
import csv
import io
from classifier import classify_po

st.set_page_config(page_title="PO Category Classifier", layout="centered")

st.markdown(
    """
    <style>
    .stApp {
        background: #f7f4ef;
    }

    .app-card {
        max-width: 760px;
        margin: 0 auto;
        padding: 24px 28px 20px;
        background: #ffffff;
        border: 1px solid #e7e2d7;
        border-radius: 14px;
        box-shadow: 0 10px 32px rgba(0, 0, 0, 0.08);
    }

    .app-title {
        color: #2c2c2c !important;
        font-family: "Georgia", serif;
        font-weight: 600;
        margin-bottom: 4px;
    }

    .app-subtitle {
        color: #2c2c2c !important;
        font-family: "Georgia", serif;
        font-weight: 600;
        margin: 18px 0 6px;
    }

    .stCaption {
        color: #2c2c2c !important;
    }

    label, .stTextInput label, .stTextArea label {
        color: #2c2c2c !important;
        font-weight: 600;
    }

    textarea, input {
        color: #1f1f1f !important;
        background: #ffffff !important;
        border-radius: 10px !important;
        border: 1px solid #d7d1c6 !important;
        padding: 10px 12px !important;
        font-size: 15px !important;
    }

    textarea::placeholder, input::placeholder {
        color: #6a6a6a !important;
        opacity: 1;
    }

    .stButton > button {
        width: 100%;
        background: #c0392b;
        color: #ffffff;
        padding: 12px 14px;
        font-weight: 600;
        border-radius: 12px;
        border: none;
    }

    .stTabs [data-baseweb="tab"] {
        background: #c0392b;
        color: #ffffff;
        border-radius: 10px;
        padding: 6px 14px;
        margin-right: 8px;
    }

    .stTabs [data-baseweb="tab"][aria-selected="true"] {
        background: #922b21;
        color: #ffffff;
    }
    </style>
    """,
    unsafe_allow_html=True
)

st.markdown("<div class='app-card'>", unsafe_allow_html=True)

st.markdown("<h1 class='app-title'>PO L1-L2-L3 Classifier</h1>", unsafe_allow_html=True)
st.caption("Paste a PO description and (optionally) a supplier. Get structured category output.")

if "po_description" not in st.session_state:
    st.session_state["po_description"] = ""
if "supplier" not in st.session_state:
    st.session_state["supplier"] = ""
if "result_raw" not in st.session_state:
    st.session_state["result_raw"] = None
if "result_json" not in st.session_state:
    st.session_state["result_json"] = None
if "result_error" not in st.session_state:
    st.session_state["result_error"] = None
if "last_inputs" not in st.session_state:
    st.session_state["last_inputs"] = ("", "")
if "clear_requested" not in st.session_state:
    st.session_state["clear_requested"] = False
if "batch_results" not in st.session_state:
    st.session_state["batch_results"] = []
if "batch_error" not in st.session_state:
    st.session_state["batch_error"] = None
if "batch_uploader_key" not in st.session_state:
    st.session_state["batch_uploader_key"] = 0

def clear_results() -> None:
    st.session_state["result_raw"] = None
    st.session_state["result_json"] = None
    st.session_state["result_error"] = None

def clear_form() -> None:
    st.session_state["po_description"] = ""
    st.session_state["supplier"] = ""
    clear_results()
    st.session_state["last_inputs"] = ("", "")

def apply_sample(description: str, supplier_value: str) -> None:
    st.session_state["po_description"] = description
    st.session_state["supplier"] = supplier_value
    clear_results()
    st.session_state["last_inputs"] = (description, supplier_value)

def parse_model_json(result: str):
    try:
        return json.loads(result), None
    except Exception:
        return None, "Invalid model response"

def clear_batch() -> None:
    st.session_state["batch_results"] = []
    st.session_state["batch_error"] = None
    st.session_state["batch_uploader_key"] += 1

if st.session_state["clear_requested"]:
    clear_form()
    st.session_state["clear_requested"] = False

tabs = st.tabs(["Single classify", "Batch classify"])

with tabs[0]:
    st.markdown("<h3 class='app-subtitle'>Sample inputs</h3>", unsafe_allow_html=True)
    st.caption("Click to prefill the form with an example.")
    sample_col_1, sample_col_2 = st.columns(2)
    with sample_col_1:
        st.button(
            "Office chairs",
            on_click=apply_sample,
            args=("Purchase of office chairs", "Staples"),
            use_container_width=True
        )
    with sample_col_2:
        st.button(
            "Audit services",
            on_click=apply_sample,
            args=("Annual audit services for FY2025", "Deloitte"),
            use_container_width=True
        )

    st.markdown("<h3 class='app-subtitle'>Classify a PO</h3>", unsafe_allow_html=True)
    with st.form("po-classifier-form"):
        po_description = st.text_area(
            "PO Description",
            height=140,
            placeholder="e.g., Purchase of office chairs",
            help="Include key item/service details, quantities, or contract terms.",
            key="po_description"
        )
        st.caption(f"{len(po_description.strip())} characters")
        supplier = st.text_input(
            "Supplier (optional)",
            placeholder="e.g., Staples",
            key="supplier"
        )
        submit_disabled = not po_description.strip()
        button_col_1, button_col_2 = st.columns(2)
        with button_col_1:
            submitted = st.form_submit_button("Classify PO", disabled=submit_disabled)
        with button_col_2:
            cleared = st.form_submit_button("Clear form")

    if "cleared" not in locals():
        cleared = False

    if cleared:
        st.session_state["clear_requested"] = True
        st.rerun()

    current_inputs = (po_description, supplier)
    if st.session_state["last_inputs"] != current_inputs and not submitted and not cleared:
        clear_results()
    st.session_state["last_inputs"] = current_inputs

    if submitted:
        description_value = po_description.strip()
        supplier_value = supplier.strip() or "Not provided"
        if not description_value:
            st.warning("Please enter a PO description.")
        else:
            status_note = st.empty()
            status_note.caption("Classifying...")
            with st.spinner("Classifying..."):
                try:
                    result = classify_po(description_value, supplier_value)
                except Exception as exc:
                    st.session_state["result_raw"] = None
                    st.session_state["result_json"] = None
                    st.session_state["result_error"] = ("exception", exc)
                else:
                    st.session_state["result_raw"] = result
                    parsed, error = parse_model_json(result)
                    st.session_state["result_json"] = parsed
                    st.session_state["result_error"] = None if error is None else ("json", error)
            status_note.empty()

    if (
        st.session_state["result_raw"] is not None
        or st.session_state["result_json"] is not None
        or st.session_state["result_error"] is not None
    ):
        st.markdown("<h3 class='app-subtitle'>Result</h3>", unsafe_allow_html=True)
        if st.session_state["result_error"]:
            error_type, error_detail = st.session_state["result_error"]
            if error_type == "exception":
                st.error("Something went wrong while classifying the PO.")
                st.exception(error_detail)
            else:
                st.error("Invalid model response")
        if st.session_state["result_json"] is not None:
            status_label = "Classified"
            l1_value = st.session_state["result_json"].get("L1")
            l2_value = st.session_state["result_json"].get("L2")
            l3_value = st.session_state["result_json"].get("L3")
            if "Not sure" in {l1_value, l2_value, l3_value}:
                status_label = "Needs review"
            st.caption(f"Status: {status_label}")
            st.json(st.session_state["result_json"])
            st.caption("Copyable JSON")
            st.text_area(
                "Copyable JSON",
                value=json.dumps(st.session_state["result_json"], indent=2),
                height=160
            )
        if st.session_state["result_raw"] is not None:
            with st.expander("Show raw model response"):
                st.text(st.session_state["result_raw"])

with tabs[1]:
    st.markdown("<h3 class='app-subtitle'>Batch classify</h3>", unsafe_allow_html=True)
    st.caption("Upload a CSV to classify multiple POs at once.")

    sample_csv = (
        "po_description,supplier\n"
        "Purchase of office chairs,Staples\n"
        "Annual audit services for FY2025,Deloitte\n"
    )
    st.download_button(
        "Download sample CSV",
        data=sample_csv,
        file_name="po_sample.csv",
        mime="text/csv"
    )

    batch_button_col_1, batch_button_col_2 = st.columns(2)
    with batch_button_col_1:
        st.button("Clear batch form", on_click=clear_batch, use_container_width=True)
    with batch_button_col_2:
        st.caption("Use this to reset the batch uploader and results.")

    uploaded_file = st.file_uploader(
        "CSV file",
        type=["csv"],
        key=f"batch_uploader_{st.session_state['batch_uploader_key']}"
    )
    csv_headers = []
    csv_rows = []
    if uploaded_file is not None:
        try:
            content = uploaded_file.getvalue().decode("utf-8", errors="ignore")
            reader = csv.DictReader(io.StringIO(content))
            csv_headers = reader.fieldnames or []
            csv_rows = list(reader)
            if not csv_headers:
                st.warning("No headers found in the CSV file.")
        except Exception as exc:
            st.session_state["batch_error"] = exc

    if st.session_state["batch_error"]:
        st.error("Failed to read CSV file.")
        st.exception(st.session_state["batch_error"])

    if csv_headers:
        header_lower = {h.lower(): h for h in csv_headers}
        default_desc = header_lower.get("po_description") or header_lower.get("description") or csv_headers[0]
        default_supplier = header_lower.get("supplier", "")

        with st.form("batch-form"):
            desc_col = st.selectbox("Description column", csv_headers, index=csv_headers.index(default_desc))
            supplier_options = ["(none)"] + csv_headers
            if default_supplier:
                supplier_index = supplier_options.index(default_supplier)
            else:
                supplier_index = 0
            supplier_col = st.selectbox("Supplier column", supplier_options, index=supplier_index)
            batch_submit = st.form_submit_button("Run batch classification", disabled=not csv_rows)

        if batch_submit:
            results = []
            progress = st.progress(0)
            total = len(csv_rows)
            for idx, row in enumerate(csv_rows, start=1):
                description_value = (row.get(desc_col) or "").strip()
                supplier_value = (row.get(supplier_col) or "").strip() if supplier_col != "(none)" else ""
                supplier_value = supplier_value or "Not provided"
                if not description_value:
                    results.append(
                        {
                            "row": idx,
                            "po_description": "",
                            "L1": "Not sure",
                            "L2": "Not sure",
                            "L3": "Not sure",
                            "error": "Missing description"
                        }
                    )
                else:
                    try:
                        result = classify_po(description_value, supplier_value)
                    except Exception as exc:
                        results.append(
                            {
                                "row": idx,
                                "po_description": description_value,
                                "L1": "Not sure",
                                "L2": "Not sure",
                                "L3": "Not sure",
                                "error": f"Exception: {exc}"
                            }
                        )
                    else:
                        parsed, error = parse_model_json(result)
                        if parsed:
                            parsed["row"] = idx
                            parsed["error"] = ""
                            results.append(parsed)
                        else:
                            results.append(
                                {
                                    "row": idx,
                                    "po_description": description_value,
                                    "L1": "Not sure",
                                    "L2": "Not sure",
                                    "L3": "Not sure",
                                    "error": error
                                }
                            )
                progress.progress(idx / total)
            st.session_state["batch_results"] = results

    if st.session_state["batch_results"]:
        st.markdown("<h3 class='app-subtitle'>Batch Results</h3>", unsafe_allow_html=True)
        st.dataframe(st.session_state["batch_results"], use_container_width=True)
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=st.session_state["batch_results"][0].keys())
        writer.writeheader()
        writer.writerows(st.session_state["batch_results"])
        st.download_button(
            "Download CSV",
            data=output.getvalue(),
            file_name="po_batch_results.csv",
            mime="text/csv"
        )

st.markdown("</div>", unsafe_allow_html=True)
