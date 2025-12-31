from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime
from .database import get_db, Order, OrderStatus, PaymentMode
from .schemas import OrderCreate, OrderUpdate, OrderResponse, CarrierSelectionRequest
from .engine import calculate_cost
from .zones import get_zone_column, PINCODE_LOOKUP
import json
import os

router = APIRouter(prefix="/api/orders", tags=["Orders"])

def load_rates():
    """Load rate cards from JSON file"""
    rate_card_path = os.path.join(os.path.dirname(__file__), "data", "rate_cards.json")
    try:
        with open(rate_card_path, "r") as f:
            return json.load(f)
    except Exception:
        return []

def generate_order_number(db: Session) -> str:
    """Generate unique order number"""
    from datetime import datetime
    today = datetime.utcnow()
    prefix = f"ORD-{today.year}-"

    # Get the latest order number for today
    latest_order = (
        db.query(Order)
        .filter(Order.order_number.like(f"{prefix}%"))
        .order_by(Order.id.desc())
        .first()
    )

    if latest_order:
        # Extract number and increment
        try:
            last_num = int(latest_order.order_number.split("-")[-1])
            new_num = last_num + 1
        except (ValueError, IndexError):
            new_num = 1001
    else:
        new_num = 1001

    return f"{prefix}{new_num}"


def calculate_volumetric_weight(length: float, width: float, height: float) -> float:
    """Calculate volumetric weight: (L x W x H) / 5000"""
    if length and width and height:
        return (length * width * height) / 5000
    return 0.0


@router.get("/pincode/{pincode}")
def lookup_pincode(pincode: int):
    """Get city and state for a pincode"""
    pincode_data = PINCODE_LOOKUP.get(pincode)

    if not pincode_data:
        raise HTTPException(status_code=404, detail="Pincode not found")

    return {
        "pincode": pincode,
        "city": pincode_data.get("district", ""),
        "state": pincode_data.get("state", ""),
        "office": pincode_data.get("office", "")
    }


@router.post("/", response_model=OrderResponse, status_code=status.HTTP_201_CREATED)
def create_order(order: OrderCreate, db: Session = Depends(get_db)):
    """Create a new order"""

    # Calculate volumetric weight (L x W x H / 5000)
    vol_weight = calculate_volumetric_weight(order.length, order.width, order.height)

    # Applicable weight is max of actual and volumetric
    applicable_weight = max(order.weight, vol_weight)

    # Create order
    db_order = Order(
        order_number=generate_order_number(db),
        recipient_name=order.recipient_name,
        recipient_contact=order.recipient_contact,
        recipient_address=order.recipient_address,
        recipient_pincode=order.recipient_pincode,
        recipient_city=order.recipient_city,
        recipient_state=order.recipient_state,
        recipient_phone=order.recipient_phone,
        recipient_email=order.recipient_email,
        sender_pincode=order.sender_pincode,
        sender_name=order.sender_name,
        sender_address=order.sender_address,
        sender_phone=order.sender_phone,
        weight=order.weight,
        length=order.length,
        width=order.width,
        height=order.height,
        volumetric_weight=vol_weight,
        applicable_weight=applicable_weight,
        payment_mode=PaymentMode(order.payment_mode),
        order_value=order.order_value,
        item_type=order.item_type,
        sku=order.sku,
        quantity=order.quantity,
        item_amount=order.item_amount,
        status=OrderStatus.DRAFT,
        notes=order.notes
    )

    db.add(db_order)
    db.commit()
    db.refresh(db_order)

    return db_order


@router.get("/", response_model=List[OrderResponse])
def get_orders(
    status: str = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """Get all orders with optional status filter"""
    query = db.query(Order)

    if status:
        try:
            status_enum = OrderStatus(status)
            query = query.filter(Order.status == status_enum)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid status. Must be one of: {[s.value for s in OrderStatus]}"
            )

    orders = query.order_by(Order.created_at.desc()).offset(skip).limit(limit).all()
    return orders


@router.get("/{order_id}", response_model=OrderResponse)
def get_order(order_id: int, db: Session = Depends(get_db)):
    """Get a specific order by ID"""
    order = db.query(Order).filter(Order.id == order_id).first()

    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    return order


@router.put("/{order_id}", response_model=OrderResponse)
def update_order(order_id: int, order_update: OrderUpdate, db: Session = Depends(get_db)):
    """Update an existing order"""
    db_order = db.query(Order).filter(Order.id == order_id).first()

    if not db_order:
        raise HTTPException(status_code=404, detail="Order not found")

    # Update only provided fields
    update_data = order_update.model_dump(exclude_unset=True)

    for field, value in update_data.items():
        if field == "payment_mode" and value:
            setattr(db_order, field, PaymentMode(value))
        elif field == "status" and value:
            setattr(db_order, field, OrderStatus(value))
        else:
            setattr(db_order, field, value)

    # Recalculate volumetric weight if dimensions changed
    if any(k in update_data for k in ['length', 'width', 'height', 'weight']):
        vol_weight = calculate_volumetric_weight(
            db_order.length,
            db_order.width,
            db_order.height
        )
        db_order.volumetric_weight = vol_weight
        db_order.applicable_weight = max(db_order.weight, vol_weight)

    db_order.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(db_order)

    return db_order


@router.delete("/{order_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_order(order_id: int, db: Session = Depends(get_db)):
    """Delete an order"""
    db_order = db.query(Order).filter(Order.id == order_id).first()

    if not db_order:
        raise HTTPException(status_code=404, detail="Order not found")

    # Only allow deletion of draft orders
    if db_order.status != OrderStatus.DRAFT:
        raise HTTPException(
            status_code=400,
            detail="Can only delete orders in DRAFT status"
        )

    db.delete(db_order)
    db.commit()

    return None


@router.post("/compare-carriers")
def compare_carriers_for_orders(
    order_ids: List[int],
    db: Session = Depends(get_db)
):
    """Compare carrier rates for one or more orders"""

    if not order_ids:
        raise HTTPException(status_code=400, detail="No orders provided")

    orders = db.query(Order).filter(Order.id.in_(order_ids)).all()

    if len(orders) != len(order_ids):
        raise HTTPException(status_code=404, detail="One or more orders not found")

    # For multiple orders, we'll aggregate weights and use first order's pincodes
    total_weight = sum(order.applicable_weight or order.weight for order in orders)
    source_pincode = orders[0].sender_pincode
    dest_pincode = orders[0].recipient_pincode

    # Check if COD
    is_cod = any(order.payment_mode == PaymentMode.COD for order in orders)
    total_order_value = sum(order.order_value for order in orders if order.payment_mode == PaymentMode.COD)

    # Get zone
    zone_key, zone_label = get_zone_column(source_pincode, dest_pincode)

    # Load carriers
    rates = load_rates()
    results = []

    for carrier in rates:
        if not carrier.get("active", True):
            continue

        try:
            res = calculate_cost(
                weight=total_weight,
                zone_key=zone_key,
                carrier_data=carrier,
                is_cod=is_cod,
                order_value=total_order_value
            )

            res["applied_zone"] = zone_label
            res["mode"] = carrier.get("mode", "Surface")
            res["order_count"] = len(orders)
            res["total_weight"] = total_weight
            results.append(res)

        except Exception as e:
            continue

    if not results:
        raise HTTPException(
            status_code=404,
            detail="No active carriers found"
        )

    return {
        "orders": [
            {
                "id": order.id,
                "order_number": order.order_number,
                "recipient_name": order.recipient_name,
                "weight": order.applicable_weight or order.weight
            }
            for order in orders
        ],
        "carriers": sorted(results, key=lambda x: x["total_cost"]),
        "source_pincode": source_pincode,
        "dest_pincode": dest_pincode,
        "total_weight": total_weight
    }


@router.post("/book-carrier")
def book_carrier(
    booking: CarrierSelectionRequest,
    db: Session = Depends(get_db)
):
    """Book a carrier for selected orders"""

    orders = db.query(Order).filter(Order.id.in_(booking.order_ids)).all()

    if len(orders) != len(booking.order_ids):
        raise HTTPException(status_code=404, detail="One or more orders not found")

    # Calculate rates for the selected carrier
    total_weight = sum(order.applicable_weight or order.weight for order in orders)
    source_pincode = orders[0].sender_pincode
    dest_pincode = orders[0].recipient_pincode
    is_cod = any(order.payment_mode == PaymentMode.COD for order in orders)
    total_order_value = sum(order.order_value for order in orders if order.payment_mode == PaymentMode.COD)

    zone_key, zone_label = get_zone_column(source_pincode, dest_pincode)

    # Find the carrier
    rates = load_rates()
    carrier_data = None
    for carrier in rates:
        if carrier.get("carrier_name") == booking.carrier_name and carrier.get("mode") == booking.mode:
            carrier_data = carrier
            break

    if not carrier_data:
        raise HTTPException(status_code=404, detail="Carrier not found")

    # Calculate cost
    cost_result = calculate_cost(
        weight=total_weight,
        zone_key=zone_key,
        carrier_data=carrier_data,
        is_cod=is_cod,
        order_value=total_order_value
    )

    # Update all orders
    for order in orders:
        order.selected_carrier = booking.carrier_name
        order.mode = booking.mode
        order.zone_applied = zone_label
        order.total_cost = cost_result["total_cost"]
        order.cost_breakdown = cost_result["breakdown"]
        order.status = OrderStatus.BOOKED
        order.booked_at = datetime.utcnow()
        order.updated_at = datetime.utcnow()

    db.commit()

    return {
        "status": "success",
        "message": f"{len(orders)} order(s) booked with {booking.carrier_name}",
        "orders_updated": [order.order_number for order in orders],
        "total_cost": cost_result["total_cost"],
        "carrier": booking.carrier_name,
        "mode": booking.mode
    }
