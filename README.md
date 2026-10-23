# ClearEntry — AI Customs Documentation & Compliance Checker

A beginner-friendly Streamlit prototype using CrewAI and Groq. It compares a commercial invoice and packing list, retrieves relevant passages from regulation files supplied by the user (lightweight keyword-based RAG), and drafts a preliminary issue report. It can optionally send the report summary to an n8n webhook.

## Important limitations

- This is a prototype, not legal advice, a customs ruling, or a customs filing system.
- It does not connect to a live tariff database or guarantee that uploaded regulations are current or complete.
- The RAG search is a lightweight lexical/keyword retriever, not a vector database. For production, replace it with a maintained vector store and embeddings.
- Scanned PDFs require OCR before upload. Text extraction alone cannot read scanned pages.
- Do not upload sensitive trade documents unless you have permission and understand the data-handling terms of the services you use.

## Files

- `app.py`: Streamlit UI and file upload flow
- `crew.py`: CrewAI task orchestration and Groq model configuration
- `agents/`: one Python file per specialized agent
- `tools/document_tools.py`: file reading, cross-document scan, regulation retrieval, report structure
- `requirements.txt`: Python dependencies

## Model

Default model: `openai/gpt-oss-120b` through Groq's API. Change the `GROQ_MODEL` secret/environment variable if you want another model supported by your Groq account.

CrewAI uses its LiteLLM adapter for Groq (`groq/<model-id>`), while the model ID remains `openai/gpt-oss-120b`.

## Secrets

For Streamlit Community Cloud, add this under App settings → Secrets:

```toml
GROQ_API_KEY = "your-real-groq-api-key"
GROQ_MODEL = "openai/gpt-oss-120b"
```

Never commit a real API key to GitHub.

## n8n integration

In n8n, create a workflow with a Webhook trigger that accepts POST requests and optionally a following action such as email, Google Sheets, or a notification. Publish/activate the workflow and copy its production webhook URL into the app. Test the workflow before using it with real data. The app sends filenames, jurisdiction, shipment type, and the report text only—not the original file bytes.

## Security note

The app sends document text to Groq as part of the AI review. Review Groq's terms and your organization's privacy requirements before using real commercial documents.
