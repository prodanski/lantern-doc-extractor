import streamlit as st
import tempfile
import json
import uuid
import pandas as pd
from io import BytesIO  

from extractor import ask_doc_questions


demo_fields = [
        {
            "id": str(uuid.uuid4()),
            "name": "Name",
            "question": "What is the name of the applicant?",
            "terms": "applicant"
        },
        {
            "id": str(uuid.uuid4()),
            "name": "Account Number",
            "question": "What is the IBAN or account number?",
            "terms": "bank, iban, account number, account"
        },
        {
            "id": str(uuid.uuid4()),
            "name": "Sort Code",
            "question": "What is the sort code or SWIFT?",
            "terms": "bank, iban, swift, sort code"
        },
        {
            "id": str(uuid.uuid4()),
            "name": "Bank Name",
            "question": "What is the bank name?",
            "terms": "bank, bank:, building society"
        },
        {
            "id": str(uuid.uuid4()),
            "name": "Commitment Amount",
            "question": "How much is the commitment ammount?",
            "terms": "#num"
        },
        {
            "id": str(uuid.uuid4()),
            "name": "Commitment Currency",
            "question": "What is the commitment currency?",
            "terms": "euro, eur, gbp, usd"
        },
        {
            "id": str(uuid.uuid4()),
            "name": "Investor Email",
            "question": "What is the investor email?",
            "terms": "@"
        },
    ]

# --- UI ---
st.set_page_config(layout="wide")
st.title("Document Extraction")
st.caption("Cezar Prodan for LANTERN")
st.write("Upload a PDF and extract structured fields.")
st.markdown("### How to use:")
st.write("This is a small-LLM powered document extractor. For each thing you'd like to know add a field name below. Then write the question that would help the LLM extract what you're looking for.")
st.markdown("Optionally, to speed things, you can add search terms. With these you help the model by telling it where to look first. \n Separate each term with a comma.")
st.markdown("Type in _#num_ if you want the model to look for numbers.")
progress_bar = st.progress(0)
def update_progress(p):
    progress_bar.progress(p)
if "fields" not in st.session_state:
    st.session_state.fields = [
        {
            "id": str(uuid.uuid4()),
            "name": "Name",
            "question": "What is the name of the applicant?",
            "terms": "applicant"
        }
    ]

st.subheader("Extraction Fields")
st.write("Search terms are optional. Use commas to separate multiple terms.")
col1, col2 = st.columns(2)

with col1:
    if st.button("Add field"):
        st.session_state.fields.append({
            "id": str(uuid.uuid4()),
            "name": "",
            "question": "",
            "terms": ""
        })
        st.rerun()

with col2:
    if st.button("Demo Fields"):
        st.session_state.fields = demo_fields.copy()
        st.rerun()


for field in st.session_state.fields:
    fid = field["id"]

    #st.markdown("### Field")

    col1, col2, col3, col4 = st.columns([2, 3, 3, 1])

    field["name"] = col1.text_input(
        "Field name",
        value=field["name"],
        key=f"name_{fid}"
    )

    field["question"] = col2.text_input(
        "Question",
        value=field["question"],
        key=f"question_{fid}"
    )

    field["terms"] = col3.text_input(
        "Search terms (optional)",
        value=field["terms"],
        key=f"terms_{fid}"
    )

    if col4.button("-", key=f"remove_{fid}"):
        st.session_state.fields = [
            f for f in st.session_state.fields if f["id"] != fid
        ]
        st.rerun()

questions = {}
terms = {}

for field in st.session_state.fields:
    name = field["name"].strip()
    
    if not name:
        continue

    questions[name] = field["question"]
    
    # split comma-separated terms
    terms[name] = [
        t.strip() for t in field["terms"].split(",") if t.strip()
    ] or [""]

if not questions:
    st.error("Please add at least one field")
    st.stop()


uploaded_file = st.file_uploader("Upload PDF", type=["pdf"])

if uploaded_file is not None:
    st.success("File uploaded")

    # save to temp file (your pipeline expects a path)
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        tmp.write(uploaded_file.read())
        tmp_path = tmp.name

    if st.button("Run Extraction"):
        with st.spinner("Running extraction..."):
            results, pages = ask_doc_questions(
                tmp_path,
                questions,
                terms,
                verbose=0,
                progress_callback=update_progress)

        st.subheader("Results")

        # pretty display
        formatted = []
        for k, v in results.items():
            formatted.append({
                "field": k,
                "answer": v['answer'],
                "confidence": str(100 * round(v['score'], 3))+"%",
                "page": v['page']
            })

        df = pd.DataFrame(formatted)
        st.dataframe(df)

        # raw JSON (nice touch)
        with st.expander("Raw Output"):
            st.json(results)

        # debug info (optional but useful signal)
        with st.expander("Page Map"):
            st.json(pages)

        output = BytesIO()

        with pd.ExcelWriter(output, engine="openpyxl") as writer:
            df.to_excel(writer, index=False, sheet_name="results")

        excel_data = output.getvalue()
        st.download_button(
            label="Download Excel",
            data=excel_data,
            file_name="extraction_results.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )