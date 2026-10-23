from crewai import Agent

def build_cross_validator(llm, compare_tool, status_callback):
    return Agent(
        role="Cross-Document Audit Specialist",
        goal="Identify material inconsistencies and missing fields across shipment documents, supported by exact evidence.",
        backstory="You compare trade paperwork carefully and distinguish confirmed mismatches from ambiguous or absent information.",
        llm=llm,
        tools=[compare_tool],
        allow_delegation=False,
        verbose=True,
        step_callback=lambda step: status_callback(),
    )
