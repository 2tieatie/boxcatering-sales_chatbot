"""Orders API endpoints."""

from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Order, User
from app.schemas.order import OrderResponse, OrderUpdate
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
    
    # Filter by status if specified
    if status:
        query = query.filter(Order.status == status)
    
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
