import json
from datetime import datetime, timezone
from tools import TOOL_MAP

class HookContext:
    """Tracks session state for hook enforcement."""
    def __init__(self):
        self.verified_customer_id: str | None = None
        self.tool_calls: list[str] = []
        self.logs: list[str] = []


def pre_tool_use_hook(tool_name: str, tool_input: dict, ctx: HookContext) -> dict | None:
    """
    Fires BEFORE tool execution.
    Returns an error dict to block the call, or None to allow it.

    Gate pattern: process_refund and lookup_order require prior get_customer success.
    This is deterministic -- prompt instructions alone cannot bypass it.
    """
    ctx.tool_calls.append(tool_name)

    if tool_name in ("process_refund", "lookup_order"):
        if ctx.verified_customer_id is None:
            return {
                "isError": True,
                "errorCategory": "validation",
                "isRetryable": True,
                "message": (
                    f"HOOK BLOCKED: {tool_name} requires a verified customer identity. "
                    "Call get_customer first to verify the customer, then retry."
                )
            }

    if tool_name == "process_refund":
        amount = tool_input.get("amount", 0)
        if amount > 500:
            # Hard cap: block and force escalation (Pillar 3)
            return {
                "isError": True,
                "errorCategory": "business",
                "isRetryable": False,
                "message": (
                    f"HOOK BLOCKED: Refund amount ${amount:.2f} exceeds the $500 automation limit. "
                    "Policy requires human approval for refunds above $500. "
                    "Call escalate_to_human with recommended_action='Approve manual refund "
                    f"${amount:.2f} -- exceeds automation threshold'."
                )
            }

    return None  # allow


def post_tool_use_hook(tool_name: str, tool_input: dict, result: dict, ctx: HookContext) -> dict:
    """
    Fires AFTER tool execution, before result is appended to conversation.
    Normalizes data and updates session state.
    """
    # Update verified customer state
    if tool_name == "get_customer" and not result.get("isError"):
        ctx.verified_customer_id = result.get("customer_id")

    # PostToolUse normalization (Pillar 3): already ISO 8601 dates in mock,
    # but enforce here so real backends with Unix timestamps get normalized.
    if "date" in result and isinstance(result["date"], (int, float)):
        result["date"] = datetime.fromtimestamp(result["date"], tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    return result


def execute_tool(tool_name: str, tool_input: dict, ctx: HookContext) -> dict:
    """Run pre-hook -> tool -> post-hook pipeline."""
    # PreToolUse gate
    blocked = pre_tool_use_hook(tool_name, tool_input, ctx)
    if blocked:
        log_msg = f"[PreToolUse] {tool_name} BLOCKED -- {blocked['message'][:80]}..."
        print(f"  {log_msg}")
        ctx.logs.append(log_msg)
        return blocked

    # Execute
    fn = TOOL_MAP.get(tool_name)
    if not fn:
        return {
            "isError": True, "errorCategory": "validation", "isRetryable": False,
            "message": f"Unknown tool: {tool_name}"
        }

    log_msg = f"[Tool] {tool_name}({json.dumps(tool_input, separators=(',', ':'))})"
    print(f"  {log_msg}")
    ctx.logs.append(log_msg)
    result = fn(**tool_input)

    # PostToolUse normalization
    result = post_tool_use_hook(tool_name, tool_input, result, ctx)

    status = "error" if result.get("isError") else "ok"
    status_log = f"-> {status}: {str(result)[:100]}"
    print(f"  {status_log}")
    ctx.logs.append(status_log)
    return result
