import crewai.llms.cache as _crewai_cache
_crewai_cache.mark_cache_breakpoint = lambda msg: msg
import os
from crewai import Crew, Process, Task, LLM

from agents.document_extractor import build_document_extractor
from agents.cross_validator import build_cross_validator
from agents.regulation_researcher import build_regulation_researcher
from agents.compliance_analyst import build_compliance_analyst
from tools.document_tools import DocumentReaderTool, CrossDocumentCompareTool, RegulationSearchTool, ReportStructureTool

MODEL_NAME = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")

def run_compliance_crew(
    invoice_path,
    packing_path,
    invoice_name,
    packing_name,
    jurisdiction,
    shipment_type,
    regulation_texts,
    status_callback=None,
):
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise RuntimeError("GROQ_API_KEY is missing. Add it to Streamlit secrets.")

    # CrewAI uses LiteLLM's Groq provider adapter for this model.
    llm = LLM(
        model=f"groq/{MODEL_NAME}",
        api_key=api_key,
        temperature=0.1,
        max_tokens=5000,
    )

    def status(name, detail):
        if status_callback:
            status_callback(name, detail)

    document_reader = DocumentReaderTool()
    compare_tool = CrossDocumentCompareTool()
    regulation_tool = RegulationSearchTool(regulation_texts=regulation_texts)
    report_tool = ReportStructureTool()

    extractor = build_document_extractor(llm, document_reader, lambda: status("Document Extractor", "Reading invoice and packing-list text."))
    auditor = build_cross_validator(llm, compare_tool, lambda: status("Cross-Document Auditor", "Comparing extracted shipment fields."))
    researcher = build_regulation_researcher(llm, regulation_tool, lambda: status("Regulation Researcher", "Retrieving relevant passages from your uploaded regulation library."))
    analyst = build_compliance_analyst(llm, report_tool, lambda: status("Compliance Analyst", "Prioritizing issues and preparing the report."))

    extraction_task = Task(
        description=(
            "Use the DocumentReaderTool to read BOTH files. Invoice path: {invoice_path}; "
            "Packing list path: {packing_path}. Extract all visible fields faithfully. "
            "Keep invoice and packing list clearly separated. Do not guess unreadable values. "
            "Flag fields absent from the documents. Shipment type: {shipment_type}; jurisdiction: {jurisdiction}."
        ),
        expected_output="A structured, source-faithful extraction of the invoice and packing list, with missing or unreadable fields explicitly marked.",
        agent=extractor,
    )
    comparison_task = Task(
        description=(
            "Audit the invoice and packing list for inconsistencies. Use CrossDocumentCompareTool on the extracted "
            "document contents. Compare descriptions, quantities, weights, package counts, dates, currency, totals, "
            "and HS-code references if present. Distinguish an actual mismatch from a field that simply is not shown. "
            "Do not invent values."
        ),
        expected_output="A list of matching fields, discrepancies, missing fields, and the exact evidence from each document.",
        agent=auditor,
        context=[extraction_task],
    )
    regulation_task = Task(
        description=(
            "Research potentially relevant requirements for this {jurisdiction} {shipment_type} shipment. "
            "You MUST use RegulationSearchTool to retrieve relevant passages from the user-uploaded regulation library. "
            "For each passage, state its uploaded source filename and quote or accurately summarize the relevant wording. "
            "If the supplied library does not establish a rule, say 'not established by supplied sources'. "
            "Never invent legal citations or imply that retrieved user files are a complete/current law database."
        ),
        expected_output="Relevant retrieved source passages with filename, rule summary, applicability notes, and limitations.",
        agent=researcher,
        context=[extraction_task, comparison_task],
    )
    report_task = Task(
        description=(
            "Prepare a professional preliminary compliance report for {jurisdiction}, shipment type {shipment_type}. "
            "Use the extraction, cross-document audit, and retrieved regulation evidence. Use ReportStructureTool to "
            "organize the findings. Include: executive summary; high/medium/low priority issues; document evidence; "
            "regulation source and caveats; missing information; recommended human follow-up; limitations. "
            "Every legal/compliance claim must be tied to the supplied source text or clearly marked as a general check. "
            "Do not certify compliance or provide a definitive customs ruling."
        ),
        expected_output="A readable Markdown report with prioritized findings, evidence, regulation source filenames, and human review actions.",
        agent=analyst,
        context=[extraction_task, comparison_task, regulation_task],
    )

    crew = Crew(
        agents=[extractor, auditor, researcher, analyst],
        tasks=[extraction_task, comparison_task, regulation_task, report_task],
        process=Process.sequential,
        verbose=True,
    )

    result = crew.kickoff(inputs={
        "invoice_path": invoice_path,
        "packing_path": packing_path,
        "invoice_name": invoice_name,
        "packing_name": packing_name,
        "jurisdiction": jurisdiction,
        "shipment_type": shipment_type,
    })

    return {
        "report": str(report_task.output or result),
        "extraction": str(extraction_task.output or ""),
        "cross_document_audit": str(comparison_task.output or ""),
        "regulation_research": str(regulation_task.output or ""),
    }
