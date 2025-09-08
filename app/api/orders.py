"""Orders API endpoints."""

from typing import List
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Order, User
from app.schemas.order import OrderResponse, OrderUpdate, OrderCreate
from app.dependencies import get_current_active_user_dependency, role_service

router = APIRouter(prefix="/orders", tags=["orders"])


@router.get("/", response_model=List[OrderResponse])
async def get_orders(
    skip: int = 0, 
    limit: int = 100,
    status: str = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user_dependency)
):
    """Get list of orders (all authenticated users can view)."""
    query = db.query(Order)
    
    # Filter by status if specified (using state)
    if status:
        query = query.filter(Order.state == status)
    
    orders = query.offset(skip).limit(limit).all()
    return orders


@router.get("/{order_id}", response_model=OrderResponse)
async def get_order(
    order_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user_dependency)
):
    """Get order by ID (all authenticated users can view)."""
    order = db.query(Order).filter(Order.id == order_id).first()
    if order is None:
        raise HTTPException(status_code=404, detail="Order not found")
    return order


@router.put("/{order_id}", response_model=OrderResponse)
async def update_order(
    order_id: int,
    order_data: OrderUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user_dependency)
):
    """Update order (managers can only mark as processed, admins can update more fields)."""
    order = db.query(Order).filter(Order.id == order_id).first()
    if order is None:
        raise HTTPException(status_code=404, detail="Order not found")
    
    update_data = order_data.model_dump(exclude_unset=True)
    
    # Role-based update restrictions
    if current_user.role == "manager":
        # Managers can only update status to mark as processed
        allowed_fields = {"status"}
        update_data = {k: v for k, v in update_data.items() if k in allowed_fields}
        
        # Managers can only set status to "processed"
        if "status" in update_data and update_data["status"] != "processed":
            raise HTTPException(
                status_code=403, 
                detail="Managers can only mark orders as processed"
            )
    
    # Update fields
    for field, value in update_data.items():
        setattr(order, field, value)
    
    db.commit()
    db.refresh(order)
    return order


@router.post("/{order_id}/mark-processed")
async def mark_order_processed(
    order_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user_dependency)
):
    """Mark order as processed (managers only)."""
    if current_user.role != "manager":
        raise HTTPException(
            status_code=403, 
            detail="Only managers can mark orders as processed"
        )
    
    order = db.query(Order).filter(Order.id == order_id).first()
    if order is None:
        raise HTTPException(status_code=404, detail="Order not found")
    
    order.status = "processed"
    db.commit()
    
    return {"message": "Order marked as processed successfully"}


@router.get("/customer/{customer_id}", response_model=List[OrderResponse])
async def get_customer_orders(
    customer_id: int,
    skip: int = 0, 
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user_dependency)
):
    """Get orders for a specific customer (all authenticated users can view)."""
    orders = db.query(Order).filter(
        Order.customer_id == customer_id
    ).offset(skip).limit(limit).all()
    return orders


@router.post("/", response_model=OrderResponse, status_code=status.HTTP_201_CREATED)
async def create_order(
    order_data: OrderCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user_dependency),
):
    """Create a new order.

    Allowed for Manager, Admin, or System Admin. Generates a sequential order number.
    """
    role_service.require_manager_or_higher(current_user)

    # Generate a simple order number: ORD-YYYYMMDD-<increment>
    today_prefix = datetime.now(timezone.utc).strftime("%Y%m%d")
    base_prefix = f"ORD-{today_prefix}-"
    last = (
        db.query(Order)
        .filter(Order.order_number.like(f"{base_prefix}%"))
        .order_by(Order.id.desc())
        .first()
    )
    try:
        last_seq = int((last.order_number or "").split("-")[-1]) if last else 0
    except Exception:
        last_seq = 0
    next_seq = last_seq + 1
    order_number = f"{base_prefix}{next_seq:04d}"

    # Resolve or create customer if customer_id is not provided
    customer_id = order_data.customer_id
    if customer_id is None:
        from app.models import Customer
        # Try find by email, then by phone
        customer = None
        if order_data.customer_email:
            customer = db.query(Customer).filter(Customer.email == order_data.customer_email).first()
        if not customer and order_data.customer_phone:
            customer = db.query(Customer).filter(Customer.phone == order_data.customer_phone).first()
        if not customer and order_data.customer_name:
            # Create minimal customer record
            customer = Customer(
                name=order_data.customer_name,
                email=order_data.customer_email,
                phone=order_data.customer_phone,
                address=order_data.customer_address,
            )
            db.add(customer)
            db.commit()
            db.refresh(customer)
        if not customer:
            raise HTTPException(status_code=400, detail="Customer info is required to create an order")
        customer_id = customer.id

    new_order = Order(
        order_number=order_number,
        customer_id=customer_id,
        conversation_id=order_data.conversation_id,
        state=order_data.state or getattr(Order, 'state').default.arg,  # default to model default
        total_amount=order_data.total_amount or 0,
        currency=order_data.currency or "UAH",
        delivery_date=order_data.delivery_date,
        delivery_time=order_data.delivery_time,
        menu_items=order_data.menu_items,
        notes=order_data.notes,
    )
    db.add(new_order)
    # If order references a conversation, ensure that conversation points to this customer
    try:
        if new_order.conversation_id:
            from app.models import Conversation
            conv = db.query(Conversation).filter(Conversation.id == new_order.conversation_id).first()
            if conv and (conv.customer_id is None):
                conv.customer_id = customer_id
    except Exception:
        pass
    db.commit()
    db.refresh(new_order)
    return new_order
