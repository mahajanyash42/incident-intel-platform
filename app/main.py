"""
Streamlit UI for the Incident Intelligence Platform.
Lets an engineer describe an incident (optionally with a screenshot),
and see the agent's root-cause analysis report.
"""
import os
import sys
import tempfile

import streamlit as st

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
from src.agent.graph import run_agent
from src.ingestion.ocr_pipeline import extract_text_from_image

st.set_page_config(page_title="Incident Intelligence Platform", page_icon="🔍", layout="centered")

st.title("🔍 AI Incident Intelligence Platform")
st.caption("Describe an incident, optionally attach a screenshot, and get an evidence-backed root-cause analysis.")

st.divider()

# --- Input section ---
incident_description = st.text_area(
    "Incident description",
    placeholder="e.g. Checkout API returning 504 errors, users unable to complete payment. Started ~10 minutes ago.",
    height=120,
)

uploaded_screenshot = st.file_uploader(
    "Optional: attach a screenshot (error dialog, terminal output, stack trace)",
    type=["png", "jpg", "jpeg"],
)

run_button = st.button("Run Root-Cause Analysis", type="primary")

# --- Processing ---
if run_button:
    if not incident_description and not uploaded_screenshot:
        st.warning("Please enter a description or attach a screenshot.")
    else:
        combined_input = incident_description or ""

        # If a screenshot was uploaded, run OCR and append the extracted text
        if uploaded_screenshot is not None:
            with st.spinner("Extracting text from screenshot..."):
                with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp:
                    tmp.write(uploaded_screenshot.read())
                    tmp_path = tmp.name

                ocr_text = extract_text_from_image(tmp_path)
                os.unlink(tmp_path)

            if ocr_text:
                with st.expander("OCR-extracted text from screenshot"):
                    st.code(ocr_text)
                combined_input += f"\n\nExtracted from screenshot:\n{ocr_text}"
            else:
                st.warning("No text could be extracted from the screenshot.")

        # Run the agent
        with st.spinner("Analyzing incident, searching historical data and documentation..."):
            report = run_agent(combined_input)

        st.divider()
        st.subheader("Root-Cause Analysis Report")
        st.markdown(report)