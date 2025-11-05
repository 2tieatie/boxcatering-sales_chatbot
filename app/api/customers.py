"""Customers API endpoints."""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Customer, User
from app.schemas import CustomerCreate, CustomerUpdate, CustomerResponse
from app.dependencies import get_current_active_user_dependency, role_service


router = APIRouter(prefix="/customers", tags=["customers"])


@router.get("/", response_model=List[CustomerResponse])
async def list_customers(
    skip: int = 0,
    limit: int = 100,
    search: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user_dependency),
):
    """List customers. All authenticated users can view.

    Optional substring search over name/email/phone.
    """
    query = db.query(Customer)

    if search:
        like = f"%{search}%"
        query = query.filter(
            (Customer.name.ilike(like))
            | (Customer.email.ilike(like))
            | (Customer.phone.ilike(like))
        )

    customers = query.offset(skip).limit(limit).all()
    return customers


@router.get("/{customer_id}", response_model=CustomerResponse)
async def get_customer(
    customer_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user_dependency),
):
    """Get a single customer by id. All authenticated users can view."""
    customer = db.query(Customer).filter(Customer.id == customer_id).first()
    if customer is None:
        raise HTTPException(status_code=404, detail="Customer not found")
    return customer


@router.post("/", response_model=CustomerResponse)
async def create_customer(
    customer_data: CustomerCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user_dependency),
):
    """Create a new customer. Admin or System Admin only."""
    role_service.require_admin_or_system_admin(current_user)

    new_customer = Customer(
        name=customer_data.name,
        email=customer_data.email,
        phone=customer_data.phone,
        address=customer_data.address,
        notes=customer_data.notes,
    )
    db.add(new_customer)
    db.commit()
    db.refresh(new_customer)
    return new_customer


@router.put("/{customer_id}", response_model=CustomerResponse)
async def update_customer(
    customer_id: int,
    customer_data: CustomerUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user_dependency),
):
    """Update an existing customer. Admin or System Admin only."""
    role_service.require_admin_or_system_admin(current_user)

    customer = db.query(Customer).filter(Customer.id == customer_id).first()
    if customer is None:
        raise HTTPException(status_code=404, detail="Customer not found")

    update_data = customer_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(customer, field, value)

    db.commit()
    db.refresh(customer)
    return customer


@router.delete("/{customer_id}")
async def delete_customer(
    customer_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user_dependency),
):
    """Delete a customer. Admin or System Admin only."""
    role_service.require_admin_or_system_admin(current_user)

    customer = db.query(Customer).filter(Customer.id == customer_id).first()
    if customer is None:
        raise HTTPException(status_code=404, detail="Customer not found")

    db.delete(customer)
    db.commit()
    return {"message": "Customer deleted successfully"}
