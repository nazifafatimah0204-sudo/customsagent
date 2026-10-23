from crewai import Agent

def build_document_extractor(llm, document_reader_tool, status_callback):
    return Agent(
        role="Customs Document Extraction Specialist",
        goal="Extract accurate, traceable fields from the commercial invoice and packing list without guessing.",
        backstory="You are a meticulous trade-document analyst. You preserve original values, units, currencies, dates, and document labels.",
        llm=llm,
        tools=[document_reader_tool],
        allow_delegation=False,
        verbose=True,
        step_callback=lambda step: status_callback(),
    )
