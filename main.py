from graph import build_graph
from langgraph.types import Command
import asyncio


def main():
    print("="*40)
    print("Human in the Loop Langgraph agent")
    print("="*40)

    graph = build_graph()

    user_question = input("USER: ").strip().lower()

    if user_question in ['exit', 'bye', 'quit']:
        print("AI: Goodbye !!")
        return

    initial_state = {
        "user_question": user_question,
        "tool_called": "",
        "final_answer": "",
        "approval": ""
    }

    config = {
        'configurable': {
            'thread_id': 'thread_1'
        }
    }

    intermediate_state = graph.invoke(initial_state, config)

    interrupt = intermediate_state.get("__interrupt__", None)

    if interrupt:

        interrupt_data = interrupt[0].value
        print("="*20)
        print("Human Approval Required")
        print("="*20)

        print(f"{interrupt_data["message"]}")
        print(f"{interrupt_data["action"]}")

        decision = input("approve? yes/no: ")

        final_state = graph.invoke(Command(
            resume=decision
        ), config)

        final_answer = final_state["final_answer"] or "Goodbye !!"

        print(f"AI: {final_answer}")
        return

    print(f"AI: {intermediate_state["final_answer"]}")


if __name__ == "__main__":
    main()
