from crewai import Agent

def build_regulation_researcher(llm, regulation_tool, status_callback):
    return Agent(
        role="Customs Regulation Research Specialist",
        goal="Retrieve relevant rule passages from the user's supplied regulation library and report source limitations honestly.",
        backstory="You are a cautious compliance researcher. You do not invent laws, tariff codes, citations, or jurisdiction-specific rules.",
        llm=llm,
        tools=[regulation_tool],
        allow_delegation=False,
        verbose=True,
        step_callback=lambda step: status_callback(),
    )
