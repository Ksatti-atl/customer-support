import json
import os
from openai import OpenAI
from hooks import HookContext, execute_tool
from prompts import SYSTEM_PROMPT
from tools import TOOLS

def run_agent(user_message: str, verbose: bool = True, ctx: HookContext = None) -> str:
    """
    The agentic loop using OpenAI API (GitHub Models).
    """
    github_token = os.environ.get("GITHUB_TOKEN", "")
    base_url = os.environ.get("BASE_URL", "https://models.inference.ai.azure.com")
    model = os.environ.get("MODEL", "gpt-4.1-mini")
    
    client = OpenAI(base_url=base_url, api_key=github_token)
    if ctx is None:
        ctx = HookContext()

    # Convert tools from Anthropic to OpenAI format
    openai_tools = []
    for tool in TOOLS:
        openai_tools.append({
            "type": "function",
            "function": {
                "name": tool["name"],
                "description": tool["description"],
                "parameters": tool["input_schema"]
            }
        })

    messages: list[dict] = [{"role": "user", "content": user_message}]

    if verbose:
        print(f"\n{'=' * 60}")
        print(f"Customer: {user_message}")
        print(f"{'=' * 60}")

    iteration = 0
    max_iterations = 20  # safety circuit breaker

    while iteration < max_iterations:
        iteration += 1

        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "system", "content": SYSTEM_PROMPT}] + messages,
            tools=openai_tools,
        )

        choice = response.choices[0]
        message = choice.message

        # Convert assistant message object to dictionary for storage in conversation history
        assistant_msg = {"role": "assistant"}
        if message.content:
            assistant_msg["content"] = message.content
        if message.tool_calls:
            assistant_msg["tool_calls"] = [
                {
                    "id": tc.id,
                    "type": tc.type,
                    "function": {
                        "name": tc.function.name,
                        "arguments": tc.function.arguments
                    }
                } for tc in message.tool_calls
            ]

        messages.append(assistant_msg)

        if verbose and message.content:
            print(f"\nAgent: {message.content}")

        # Check for termination
        if choice.finish_reason == "stop" or not message.tool_calls:
            break

        # Process tool calls
        for tool_call in message.tool_calls:
            tool_name = tool_call.function.name
            tool_args = json.loads(tool_call.function.arguments)

            result = execute_tool(tool_name, tool_args, ctx)

            messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "name": tool_name,
                "content": json.dumps(result),
            })

    # Extract final text response from the last assistant message
    final_text = ""
    for msg in reversed(messages):
        if msg.get("role") == "assistant" and msg.get("content"):
            final_text = msg["content"]
            break

    return final_text or "(agent completed without a text response)"
