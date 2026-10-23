from crewai import Agent

def build_compliance_analyst(llm, report_tool, status_callback):
    return Agent(
        role="Compliance Report Analyst",
        goal="Produce a clear, prioritized preliminary report with evidence and practical human follow-up steps.",
        backstory="You convert document checks into an actionable report and never present AI output as official legal advice or a customs ruling.",
        llm=llm,
        tools=[report_tool],
        allow_delegation=False,
        verbose=True,
        step_callback=lambda step: status_callback(),
    )
