import streamlit as st
import tempfile
import json

from extractor import ask_doc_questions

# --- Load config once ---
with open("config/extraction_config.json", "r") as f:
    cfg = json.load(f)

questions = cfg["questions"]
terms = cfg["terms"]

# --- UI ---
st.title("Document Extraction Demo")

st.write("Upload a PDF and extract structured fields.")
verbose = st.checkbox("Show debug info", value=False)

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
                verbose=int(verbose)
            )

        st.subheader("Results")

        # pretty display
        formatted = []
        for k, v in results.items():
            formatted.append({
                "field": k,
                "answer": v['answer'],
                "confidence": round(v['score'], 3),
                "page": v['page']
            })

        st.table(formatted)

        # raw JSON (nice touch)
        with st.expander("Raw Output"):
            st.json(results)

        # debug info (optional but useful signal)
        with st.expander("Page Map"):
            st.json(pages)