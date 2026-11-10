from langgraph.graph import StateGraph, START, END
from langgraph.types import interrupt
from langgraph.checkpoint.memory import InMemorySaver
import os
from groq import Groq
from dotenv import load_dotenv
from typing import TypedDict

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_MODEL_NAME = os.getenv("GROQ_MODEL_NAME")


groq_client = Groq(api_key=GROQ_API_KEY)


def create_tool_node():
    def internal_tool(state: AgentState):
        '''
        It is a internal tool.
        it generally can answer questions regarding any employee like name , designation , team , experience, mwork modules the person owns
        , manager , subordinates.
        it can also answer policy related questions like number of leaves , HR policy , notice period , expel policy
        '''
        return {'final_answer': "internal tool has been executed"}
    return internal_tool


def create_llm_node():
    def ask_llm(state: AgentState):
        '''
        It is a external tool.
        it takes user question, asks groq llm and get answer
        '''

        user_prompt = f"""
        You are an AI assistant.

        You take user question represented by : {state["user_question"]}
        use your LLM capability and give most clean and capable and honest and appropriate answer.
        human will have to read and understand, so language should be simple.

        Do not make any answer length unless asked and highlight the main points only.
        """
        ai_response = groq_client.chat.completions.create(model=GROQ_MODEL_NAME, messages=[{
            'role': 'user',
            'content': user_prompt
        }])

        return {'final_answer': ai_response.choices[0].message.content.strip()}
    return ask_llm


tools = [
    {
        'tool_name': 'internal_tool',
        'tool_description': '''
        It is a internal tool.
        it generally can answer questions regarding any employee like name , designation , team , experience, mwork modules the person owns
        , manager , subordinates.
        it can also answer policy related questions like number of leaves , HR policy , notice period , expel policy
        '''
    },
    {
        'tool_name': 'ask_llm',
        'tool_description': '''
        It is a external tool.
        it takes user question, asks groq llm and get answer
        '''
    }
]


def create_planner_node(tools):
    def planner(state: AgentState):
        planner_prompt = f"""
        You are an AI planning assistant.

        You are responsible to give back next tool which should be executed based on user question
        choose only out of available tools.
        do not guess or invent a tool.
        only send the tool_name and nothing else.
        Do not send any explanation or anything

        eg - employee_tools

        available tools: {tools}
        user question: {state["user_question"]}
        
        """
        ai_response = groq_client.chat.completions.create(model=GROQ_MODEL_NAME, messages=[{
            'role': 'user',
            'content': planner_prompt
        }])

        return {'tool_called': ai_response.choices[0].message.content.strip()}
    return planner


class AgentState(TypedDict):
    user_question: str
    tool_called: str
    final_answer: str
    approval: str


def human_node(state: AgentState):
    decision = interrupt(
        {
            "message": "Approve this tool call?",
            "action": state["tool_called"]
        }
    )

    return {"approval": decision}


def planner_route_decision(state: AgentState):
    if state['tool_called'] == 'internal_tool':
        return 'internal'
    return 'llm'


def internal_route_decision(state: AgentState):
    if state['approval'] == 'yes':
        return 'yes'
    return 'no'


def build_graph():

    builder = StateGraph(AgentState)

    builder.add_node("planner", create_planner_node(tools))
    builder.add_node("tool", create_tool_node())
    builder.add_node("llm", create_llm_node())
    builder.add_node("hitl", human_node)

    builder.add_edge(START, "planner")

    builder.add_conditional_edges("planner", planner_route_decision, {
        'internal': 'hitl',
        'llm': 'llm'
    })

    builder.add_conditional_edges("hitl", internal_route_decision, {
        'yes': 'tool',
        'no': END
    })

    builder.add_edge("tool", END)
    builder.add_edge("llm", END)

    checkpointer = InMemorySaver()

    return builder.compile(checkpointer=checkpointer)
