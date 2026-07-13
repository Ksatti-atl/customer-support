CUSTOMERS = {
    "C001": {"name": "Alex Rivera", "email": "alex@example.com",   "tier": "Gold",   "verified": True},
    "C002": {"name": "Sam Chen",    "email": "sam@example.com",    "tier": "Silver", "verified": True},
    "C003": {"name": "Jordan Lee",  "email": "jordan@example.com", "tier": "Bronze", "verified": True},
}

ORDERS = {
    "ORD-1001": {"customer_id": "C001", "amount": 89.99,  "status": "delivered", "date": "2026-06-15",
                 "item": "Wireless Headphones",   "refund_eligible": True},
    "ORD-1002": {"customer_id": "C001", "amount": 649.00, "status": "delivered", "date": "2026-06-20",
                 "item": "Laptop Stand Pro",      "refund_eligible": True},
    "ORD-1003": {"customer_id": "C002", "amount": 34.50,  "status": "shipped",   "date": "2026-07-01",
                 "item": "USB-C Hub",             "refund_eligible": False},
    "ORD-1004": {"customer_id": "C003", "amount": 312.00, "status": "delivered", "date": "2026-07-05",
                 "item": "Mechanical Keyboard",   "refund_eligible": True},
}

REFUNDS_PROCESSED = {}  # order_id -> refund record
