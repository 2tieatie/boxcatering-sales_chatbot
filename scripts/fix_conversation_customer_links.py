"""Backfill Conversation.customer_id from existing Orders.

Run once:
  uv run python scripts/fix_conversation_customer_links.py
"""

from typing import List, Tuple

from app.database import SessionLocal
from app.models import Order, Conversation


def find_conversations_missing_customer(session) -> List[Tuple[int, int]]:
    """Return list of (conversation_id, customer_id) pairs to link."""
    pairs: List[Tuple[int, int]] = []
    # Fetch conversations without customer
    missing: List[Conversation] = (
        session.query(Conversation).filter(Conversation.customer_id.is_(None)).all()
    )
    if not missing:
        return pairs

    missing_ids = {c.id for c in missing}
    # Find any order referencing those conversations
    orders: List[Order] = (
        session.query(Order)
        .filter(Order.conversation_id.isnot(None))
        .all()
    )
    for o in orders:
        if o.conversation_id in missing_ids and o.customer_id:
            pairs.append((o.conversation_id, o.customer_id))
    return pairs


def main() -> None:
    session = SessionLocal()
    try:
        links = find_conversations_missing_customer(session)
        if not links:
            print("No missing conversation->customer links found")
            return
        updated = 0
        for conv_id, cust_id in links:
            conv = session.query(Conversation).get(conv_id)
            if conv and conv.customer_id is None:
                conv.customer_id = cust_id
                updated += 1
        if updated:
            session.commit()
        print(f"Linked {updated} conversation(s) to customers")
    finally:
        session.close()


if __name__ == "__main__":
    main()


