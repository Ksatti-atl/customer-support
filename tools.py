import json
from data import CUSTOMERS, ORDERS, REFUNDS_PROCESSED

def _tool_get_customer(customer_id: str | None = None, email: str | None = None) -> dict:
    """Mock: verify customer identity and return profile."""
    # find by id or email
    if customer_id and customer_id in CUSTOMERS:
        c = CUSTOMERS[customer_id]
        return {"customer_id": customer_id, "name": c["name"], "email": c["email"],
                "tier": c["tier"], "verified": c["verified"]}

    if email:
        for cid, c in CUSTOMERS.items():
            if c["email"].lower() == email.lower():
                return {"customer_id": cid, "name": c["name"], "email": c["email"],
                        "tier": c["tier"], "verified": c["verified"]}

    return {
        "isError": True,
        "errorCategory": "validation",
        "isRetryable": False,
        "message": (
            f"No customer found for customer_id={customer_id!r} or email={email!r}. "
            "Ask the customer for their registered email address."
        )
    }


def _tool_lookup_order(customer_id: str, order_id: str | None = None) -> dict:
    """Mock: fetch orders for a verified customer."""
    if order_id:
        order = ORDERS.get(order_id)
        if not order:
            return {
                "isError": True, "errorCategory": "validation", "isRetryable": False,
                "message": f"Order {order_id!r} not found. Verify the order number and try again."
            }

        if order["customer_id"] != customer_id:
            return {
                "isError": True, "errorCategory": "permission", "isRetryable": False,
                "message": f"Order {order_id!r} does not belong to customer {customer_id}."
            }

        return {"order_id": order_id, **_trim_order(order)}

    # return all orders for customer
    customer_orders = [
        {"order_id": oid, **_trim_order(o)}
        for oid, o in ORDERS.items() if o["customer_id"] == customer_id
    ]

    if not customer_orders:
        return {
            "isError": True, "errorCategory": "business", "isRetryable": False,
            "message": f"No orders found for customer {customer_id}."
        }

    return {"orders": customer_orders}


def _trim_order(order: dict) -> dict:
    """Pillar 5: trim to the 5 relevant fields, discard the rest."""
    return {
        "item":            order["item"],
        "amount":          order["amount"],
        "status":          order["status"],
        "date":            order["date"],       # already ISO 8601 -> PostToolUse no-op
        "refund_eligible": order["refund_eligible"],
    }


def _tool_process_refund(customer_id: str, order_id: str, amount: float, reason: str) -> dict:
    """Mock: execute a refund (financial, irreversible)."""
    order = ORDERS.get(order_id)
    if not order:
        return {
            "isError": True, "errorCategory": "validation", "isRetryable": False,
            "message": f"Order {order_id!r} not found."
        }

    if order["customer_id"] != customer_id:
        return {
            "isError": True, "errorCategory": "permission", "isRetryable": False,
            "message": "Order does not belong to this customer."
        }

    if not order["refund_eligible"]:
        return {
            "isError": True, "errorCategory": "business", "isRetryable": False,
            "message": f"Order {order_id} is not eligible for a refund (status: {order['status']})."
        }

    if order_id in REFUNDS_PROCESSED:
        return {
            "isError": True, "errorCategory": "business", "isRetryable": False,
            "message": f"Refund already processed for order {order_id}."
        }

    if amount > order["amount"]:
        return {
            "isError": True, "errorCategory": "validation", "isRetryable": False,
            "message": f"Requested refund ${amount} exceeds order amount ${order['amount']}."
        }

    refund_id = f"REF-{order_id}-{len(REFUNDS_PROCESSED) + 1:04d}"
    REFUNDS_PROCESSED[order_id] = {"refund_id": refund_id, "amount": amount, "reason": reason}

    return {
        "refund_id": refund_id,
        "order_id":  order_id,
        "amount":    amount,
        "status":    "processed",
        "message":   (
            f"Refund of ${amount:.2f} successfully processed. "
            "Funds will appear in 3-5 business days."
        )
    }


def _tool_escalate_to_human(customer_id: str, root_cause: str, recommended_action: str,
                             case_summary: str) -> dict:
    """Mock: hand off to human agent with structured context."""
    ticket_id = f"ESC-{len(REFUNDS_PROCESSED) + 1001:04d}"

    print(f"\n{'=' * 60}")
    print(f"[ESCALATION] ESCALATION TO HUMAN AGENT -- Ticket {ticket_id}")
    print(f"{'=' * 60}")
    print(f"  Customer ID:         {customer_id}")
    print(f"  Root cause:          {root_cause}")
    print(f"  Recommended action:  {recommended_action}")
    print(f"  Case summary:        {case_summary}")
    print(f"{'=' * 60}\n")

    return {
        "ticket_id":           ticket_id,
        "status":              "escalated",
        "estimated_response":  "< 2 hours",
        "message": (
            f"Your case has been escalated (ticket {ticket_id}). "
            "A human agent will contact you within 2 hours."
        )
    }


TOOL_MAP = {
    "get_customer":      _tool_get_customer,
    "lookup_order":      _tool_lookup_order,
    "process_refund":    _tool_process_refund,
    "escalate_to_human": _tool_escalate_to_human,
}

TOOLS = [
    {
        "name": "get_customer",
        "description": (
            "Verify a customer's identity and retrieve their account profile. "
            "MUST be called before lookup_order or process_refund -- those tools require a verified customer_id. "
            "Accepts either customer_id (format: 'C001') or email address. "
            "Use email when the customer provides it directly. "
            "Example: get_customer(email='alex@example.com'). "
            "Returns: customer_id, name, email, tier (Gold/Silver/Bronze), verified flag. "
            "Do NOT call process_refund or lookup_order without a verified customer_id from this tool."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "customer_id": {"type": "string", "description": "Customer ID, e.g. 'C001'"},
                "email":       {"type": "string", "description": "Customer's registered email address"}
            }
        }
    },
    {
        "name": "lookup_order",
        "description": (
            "Retrieve order details for a verified customer. Requires a verified customer_id from get_customer. "
            "Optionally accepts order_id to fetch a specific order (format: 'ORD-1001'). "
            "Without order_id, returns all orders for the customer. "
            "Returns: item name, amount, status (delivered/shipped/processing), date (ISO 8601), refund_eligible. "
            "Use this before process_refund to confirm eligibility and exact amount. "
            "Different from get_customer -- this fetches transaction history, not identity."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "customer_id": {"type": "string", "description": "Verified customer ID from get_customer"},
                "order_id":    {"type": "string", "description": "Specific order ID, e.g. 'ORD-1001' (optional)"}
            },
            "required": ["customer_id"]
        }
    },
    {
        "name": "process_refund",
        "description": (
            "Execute a monetary refund for an eligible order. This is FINANCIAL and IRREVERSIBLE. "
            "Prerequisites: (1) customer verified via get_customer, (2) order confirmed eligible via lookup_order. "
            "Hard limit: amount must be <= $500. Amounts > $500 require human approval -- use escalate_to_human "
            "instead. "
            "Requires: customer_id (verified), order_id, amount (must match order amount exactly unless partial "
            "refund agreed), reason. "
            "Returns: refund_id, confirmation, estimated credit timeline. "
            "Do NOT call without first calling get_customer and lookup_order."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "customer_id": {"type": "string", "description": "Verified customer ID"},
                "order_id":    {"type": "string", "description": "Order ID to refund"},
                "amount":      {"type": "number", "description": "Refund amount in USD"},
                "reason":      {"type": "string", "description": "Reason for refund"}
            },
            "required": ["customer_id", "order_id", "amount", "reason"]
        }
    },
    {
        "name": "escalate_to_human",
        "description": (
            "Hand off the case to a human agent with full structured context. "
            "Use when: (1) customer explicitly requests a human -- do this IMMEDIATELY without further "
            "investigation, "
            "(2) request falls outside policy (e.g. competitor price match, refund > $500), "
            "(3) agent cannot make meaningful progress after reasonable tool attempts. "
            "DO NOT use confidence scores or sentiment to decide -- use explicit criteria above. "
            "Provide complete structured context so the human agent does not need to re-investigate."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "customer_id": {
                    "type": "string",
                    "description": "Verified customer ID (or 'unknown' if get_customer not yet called)"
                },
                "root_cause": {
                    "type": "string",
                    "description": "What was investigated and why resolution failed or escalation was needed"
                },
                "recommended_action": {
                    "type": "string",
                    "description": "Specific action for the human agent, e.g. 'Approve manual refund of $649'"
                },
                "case_summary": {
                    "type": "string",
                    "description": "Full case summary including customer request, tools called, and outcome"
                }
            },
            "required": ["customer_id", "root_cause", "recommended_action", "case_summary"]
        }
    }
]
