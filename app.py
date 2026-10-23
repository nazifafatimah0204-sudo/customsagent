import os
import tempfile
from pathlib import Path

import requests
import streamlit as st
from pypdf import PdfReader
from docx import Document

from crew import run_compliance_crew

# Streamlit Community Cloud secrets are available through st.secrets, not automatically via os.environ.
try:
    if st.secrets.get("GROQ_API_KEY"):
        os.environ["GROQ_API_KEY"] = str(st.secrets["GROQ_API_KEY"])
    if st.secrets.get("GROQ_MODEL"):
        os.environ["GROQ_MODEL"] = str(st.secrets["GROQ_MODEL"])
except Exception:
    pass

st.set_page_config(
    page_title="ClearEntry | Customs Compliance",
    page_icon="📦",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Manrope:wght@400;500;600;700;800&display=swap');
html, body, [class*="css"] { font-family: 'DM Sans', sans-serif; }
.stApp { background: #f5f7fb; }
.block-container { padding-top: 1.5rem; max-width: 1320px; }
.hero { padding: 28px 30px; border-radius: 22px; color: white;
        background: linear-gradient(120deg,#111c3a 0%,#183b68 55%,#267b83 100%);
        margin-bottom: 22px; }
.hero h1 { font-family: 'Manrope',sans-serif; font-size: 2.15rem; font-weight: 800;
           letter-spacing: -1px; margin: 0 0 8px 0; }
.hero p { color: #dbeafe; font-size: 1rem; margin: 0; max-width: 800px; }
.kicker { text-transform: uppercase; letter-spacing: 2px; font-size: .72rem;
          font-weight: 700; color: #9de6df; margin-bottom: 8px; }
.panel { background: white; border: 1px solid #e5eaf2; border-radius: 18px;
         padding: 20px 22px; margin-bottom: 14px; }
.panel h3 { margin-top: 0; font-family: 'Manrope',sans-serif; color: #14213d; }
.small-muted { color: #667085; font-size: .88rem; }
.agent-pill { border-radius: 12px; padding: 12px 14px; background: #eef6f7;
              border: 1px solid #d8eceb; margin: 7px 0; color: #174e58; }
div.stButton > button[kind="primary"] { border: 0; border-radius: 12px; padding: .72rem 1rem;
    background: linear-gradient(90deg,#176b78,#258b91); font-weight: 700; }
[data-testid="stFileUploader"] { background: white; border-radius: 14px; }
footer { visibility: hidden; }
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="hero">
  <div class="kicker">AI-assisted trade operations</div>
  <h1>ClearEntry</h1>
  <p>Customs documentation review, cross-document checks, and regulation-grounded findings — in one clear workspace.</p>
</div>
""", unsafe_allow_html=True)

with st.sidebar:
    st.markdown("## ⚙️ Review settings")
    jurisdiction = st.text_input("Country / customs jurisdiction", placeholder="e.g., Pakistan")
    shipment_type = st.selectbox("Shipment type", ["Import", "Export", "Transit", "Other"])
    st.markdown("---")
    st.markdown("### Your review team")
    st.markdown('<div class="agent-pill">🔎 <b>1 · Document Extractor</b><br><span class="small-muted">Reads source documents</span></div>', unsafe_allow_html=True)
    st.markdown('<div class="agent-pill">🧾 <b>2 · Cross-Document Auditor</b><br><span class="small-muted">Finds mismatched fields</span></div>', unsafe_allow_html=True)
    st.markdown('<div class="agent-pill">📚 <b>3 · Regulation Researcher</b><br><span class="small-muted">Retrieves relevant uploaded rules</span></div>', unsafe_allow_html=True)
    st.markdown('<div class="agent-pill">🛡️ <b>4 · Compliance Analyst</b><br><span class="small-muted">Builds an evidence-based report</span></div>', unsafe_allow_html=True)
    st.caption("AI findings are preliminary. A qualified customs professional must verify them.")

left, right = st.columns([1.05, 0.95], gap="large")
with left:
    st.markdown('<div class="panel"><h3>01 · Shipment documents</h3><p class="small-muted">Upload a commercial invoice and packing list. Supported: PDF, DOCX, TXT.</p></div>', unsafe_allow_html=True)
    invoice = st.file_uploader("Commercial invoice", type=["pdf", "docx", "txt"], key="invoice")
    packing = st.file_uploader("Packing list", type=["pdf", "docx", "txt"], key="packing")
    st.markdown('<div class="panel"><h3>02 · Regulation library (RAG)</h3><p class="small-muted">Upload the official rules, tariff notes, customs guidance, or SOPs that apply to this shipment. The app retrieves relevant passages from these files.</p></div>', unsafe_allow_html=True)
    regulations = st.file_uploader("Applicable regulations / guidance", type=["pdf", "docx", "txt"], accept_multiple_files=True, key="regulations")
with right:
    st.markdown('<div class="panel"><h3>03 · What this review checks</h3><p class="small-muted">The team checks common fields and compares them with the regulation documents you supply.</p></div>', unsafe_allow_html=True)
    st.markdown("""
    - Invoice vs. packing-list descriptions and quantities
    - Invoice values, currency, weights, dates and HS-code references where present
    - Missing or ambiguous information
    - Relevant passages retrieved from your regulation library
    - A prioritized issue list with evidence and recommended human follow-up
    """)
    st.info("Important: This prototype does not connect to a live customs tariff database. It cannot certify a declaration or guarantee legal compliance.")
    n8n_url = st.text_input("Optional n8n production webhook URL", placeholder="https://your-n8n-host/webhook/...")
    send_n8n = st.checkbox("Send the final report summary to n8n after review", value=False)
    st.caption("Only the report text and filenames are sent to n8n — not the original file bytes.")

st.markdown("---")
run_col, status_col = st.columns([1, 2], vertical_alignment="center")
with run_col:
    run_button = st.button("🚀 Run compliance review", type="primary", use_container_width=True)
with status_col:
    live_status = st.empty()

def extract_uploaded_file(uploaded):
    suffix = Path(uploaded.name).suffix.lower()
    data = uploaded.getvalue()
    if suffix == ".pdf":
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            tmp.write(data)
            tmp_path = tmp.name
        try:
            reader = PdfReader(tmp_path)
            return "\n".join(page.extract_text() or "" for page in reader.pages)
        finally:
            os.unlink(tmp_path)
    if suffix == ".docx":
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            tmp.write(data)
            tmp_path = tmp.name
        try:
            doc = Document(tmp_path)
            return "\n".join(p.text for p in doc.paragraphs)
        finally:
            os.unlink(tmp_path)
    return data.decode("utf-8", errors="replace")

def save_temp_upload(uploaded):
    suffix = Path(uploaded.name).suffix.lower()
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(uploaded.getvalue())
        return tmp.name

if run_button:
    if not invoice or not packing:
        st.error("Please upload both a commercial invoice and a packing list.")
        st.stop()
    if not jurisdiction.strip():
        st.error("Please enter the customs jurisdiction (country / authority).")
        st.stop()
    if not regulations:
        st.error("Upload at least one applicable regulation or official guidance file so the RAG tool has a source library to search.")
        st.stop()
    if send_n8n and not n8n_url.strip():
        st.error("Enter your n8n production webhook URL or uncheck the n8n option.")
        st.stop()

    temp_paths = []
    try:
        invoice_path = save_temp_upload(invoice)
        packing_path = save_temp_upload(packing)
        temp_paths.extend([invoice_path, packing_path])
        regulation_texts = []
        regulation_names = []
        for uploaded in regulations:
            text = extract_uploaded_file(uploaded)
            if text.strip():
                regulation_texts.append({"name": uploaded.name, "text": text})
                regulation_names.append(uploaded.name)
        if not regulation_texts:
            st.error("No readable text was extracted from the regulation files. If they are scanned PDFs, run OCR first and upload searchable PDFs or TXT files.")
            st.stop()

        st.markdown("### Live agent activity")
        activity = st.empty()
        completed = st.empty()
        activity.info("⏳ Initializing the CrewAI team…")
        result = run_compliance_crew(
            invoice_path=invoice_path,
            packing_path=packing_path,
            invoice_name=invoice.name,
            packing_name=packing.name,
            jurisdiction=jurisdiction.strip(),
            shipment_type=shipment_type,
            regulation_texts=regulation_texts,
            status_callback=lambda name, detail: activity.info(f"⚙️ **Working now: {name}**\n\n{detail}"),
        )
        activity.success("✅ Review workflow completed.")
        st.session_state["last_report"] = result["report"]
        st.session_state["last_result"] = result
        st.session_state["last_sources"] = regulation_names

        if send_n8n and n8n_url.strip():
            try:
                response = requests.post(
                    n8n_url.strip(),
                    json={
                        "event": "customs_review_completed",
                        "jurisdiction": jurisdiction.strip(),
                        "shipment_type": shipment_type,
                        "invoice_filename": invoice.name,
                        "packing_list_filename": packing.name,
                        "regulation_filenames": regulation_names,
                        "report": result["report"],
                    },
                    timeout=20,
                )
                response.raise_for_status()
                st.success("n8n webhook accepted the report summary.")
            except requests.RequestException as exc:
                st.warning(f"The review completed, but the n8n webhook call failed: {exc}")
    except Exception as exc:
        st.error(f"The review could not be completed. Check your Groq API key and deployment logs. Details: {exc}")
    finally:
        for path in temp_paths:
            try:
                os.unlink(path)
            except OSError:
                pass

if "last_report" in st.session_state:
    st.markdown("---")
    st.markdown("## 📋 Compliance review report")
    st.caption("Generated from the uploaded shipment documents and regulation library. Confirm every finding against the original source.")
    st.markdown(st.session_state["last_report"])
    st.download_button(
        "⬇️ Download report (.md)",
        data=st.session_state["last_report"],
        file_name="customs_compliance_report.md",
        mime="text/markdown",
    )
    with st.expander("View workflow outputs"):
        for key, value in st.session_state["last_result"].items():
            if key != "report":
                st.markdown(f"**{key.replace('_', ' ').title()}**")
                st.write(value)
    st.caption("Prototype only — not legal advice, a customs ruling, or an automated filing service.")
