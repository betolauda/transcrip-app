import streamlit as st
import requests

API_URL = "http://localhost:8000"

st.set_page_config(page_title="Argentina Economy Analyzer", layout="wide")

st.title("🇦🇷 Argentina Economy Analyzer")
st.write("Offline transcription, glossary updater, and candidate term manager.")

# --------- Upload Section ----------
st.header("Upload Audio")
uploaded_file = st.file_uploader("Choose an MP3 file", type=["mp3"])

if uploaded_file is not None:
    with st.spinner("Uploading and processing..."):
        files = {"file": (uploaded_file.name, uploaded_file, "audio/mpeg")}
        res = requests.post(f"{API_URL}/upload", files=files)
        if res.status_code == 200:
            st.success("File processed successfully")
            st.json(res.json())
        else:
            st.error(f"Error: {res.text}")

# --------- Glossaries ----------
st.header("Glossaries")

col1, col2 = st.columns(2)

with col1:
    st.subheader("Economic Glossary")
    res = requests.get(f"{API_URL}/glossaries")
    if res.status_code == 200:
        econ_terms = res.json()["economic_glossary"]
        for t, cat, ts in econ_terms:
            st.write(f"- **{t}** ({cat}, {ts})")

with col2:
    st.subheader("Argentine Dictionary")
    res = requests.get(f"{API_URL}/glossaries")
    if res.status_code == 200:
        arg_terms = res.json()["argentine_dictionary"]
        for t, ts in arg_terms:
            st.write(f"- **{t}** ({ts})")

# --------- Candidates ----------
st.header("Candidate Terms")
res = requests.get(f"{API_URL}/candidates")
if res.status_code == 200:
    candidates = res.json()["candidates"]
    if not candidates:
        st.info("No new candidates detected.")
    else:
        for term, ts, snippet in candidates:
            with st.expander(f"Candidate: {term}"):
                st.write(f"First seen: {ts}")
                st.write(f"Context: {snippet}")
                col1, col2 = st.columns(2)
                with col1:
                    if st.button(f"Promote '{term}' → Economic Glossary"):
                        promote = requests.post(f"{API_URL}/promote",
                                                params={"term": term, "glossary": "economic"})
                        if promote.status_code == 200:
                            st.success(promote.json()["message"])
                        else:
                            st.error(promote.text)
                with col2:
                    if st.button(f"Promote '{term}' → Argentine Dictionary"):
                        promote = requests.post(f"{API_URL}/promote",
                                                params={"term": term, "glossary": "argentine"})
                        if promote.status_code == 200:
                            st.success(promote.json()["message"])
                        else:
                            st.error(promote.text)
