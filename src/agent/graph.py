"""
LangGraph agent that autonomously calls search tools and synthesizes
a root-cause analysis report with citations.
"""
import os
import sys

from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, MessagesState, START, END
from langgraph.prebuilt import ToolNode, tools_condition
from dotenv import load_dotenv

sys.path.append(os.path.join(os.path.dirname(__file__), "..", ".."))
from src.agent.tools import search_similar_incidents_tool, search_technical_documents_tool

load_dotenv(override=True)  # load .env file if present, override any existing env vars

AGENT_MODEL = os.getenv("AGENT_MODEL", "gpt-4o-mini")

tools = [search_similar_incidents_tool, search_technical_documents_tool]
llm = ChatOpenAI(model=AGENT_MODEL, temperature=0)
llm_with_tools = llm.bind_tools(tools)

SYSTEM_PROMPT = """You are an SRE incident intelligence assistant. Your job is to help engineers
diagnose the root cause of production incidents by searching historical incident data and
technical documentation.

When given an incident description:
1. Search for similar historical incidents using search_similar_incidents_tool
2. Search for relevant technical documentation using search_technical_documents_tool
3. Synthesize your findings into a root-cause analysis report

Your report must include:
- Likely root cause (based on evidence found)
- Evidence: specific citations to the incidents and/or documents that support this (cite incident IDs and document/section names explicitly)
- Recommended action

IMPORTANT: If your tool searches return a "NOTE: No strong match found" warning, you must reflect
that uncertainty in your final answer. Do not present weak-confidence results as solid evidence.
In that case, clearly state that this appears to be a novel incident without strong historical
precedent, and provide your best general reasoning while being explicit that it is not backed by
prior incident data.

Always be explicit about what is evidence-backed versus your own general reasoning.
"""


def call_model(state: MessagesState):
    messages = state["messages"]
    if not any(isinstance(m, type(messages[0])) and getattr(m, "type", None) == "system" for m in messages):
        from langchain_core.messages import SystemMessage
        messages = [SystemMessage(content=SYSTEM_PROMPT)] + messages
    response = llm_with_tools.invoke(messages)
    return {"messages": [response]}


# Build the graph
graph_builder = StateGraph(MessagesState)
graph_builder.add_node("agent", call_model)
graph_builder.add_node("tools", ToolNode(tools))

graph_builder.add_edge(START, "agent")
graph_builder.add_conditional_edges("agent", tools_condition)
graph_builder.add_edge("tools", "agent")

agent_graph = graph_builder.compile()


def run_agent(incident_description: str) -> str:
    """Runs the agent on a given incident description and returns the final report text."""
    from langchain_core.messages import HumanMessage

    result = agent_graph.invoke({"messages": [HumanMessage(content=incident_description)]})
    final_message = result["messages"][-1]
    return final_message.content


if __name__ == "__main__":
    test_incident = "Checkout API returning 504 errors, users unable to complete payment. Started about 10 minutes ago."

    print(f"Incident: {test_incident}\n")
    print("Running agent...\n")

    report = run_agent(test_incident)
    print("=== FINAL REPORT ===\n")
    print(report)