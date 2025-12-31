from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional
from datetime import datetime, timedelta
from .database import get_db, Order, OrderStatus, PaymentMode
from .schemas import OrderUpdate
import json
import os

router = APIRouter(tags=["Admin Extended"])

# Settings management
@router.get("/settings")
def get_settings():
    """Get current system settings"""
    settings_path = os.path.join(os.path.dirname(__file__), "config", "settings.json")
    try:
        with open(settings_path, "r") as f:
            return json.load(f)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load settings: {str(e)}")

@router.put("/settings")
def update_settings(settings: dict):
    """Update system settings (GST, escalation, weight slab, etc.)"""
    settings_path = os.path.join(os.path.dirname(__file__), "config", "settings.json")
    try:
        # Backup current settings
        if os.path.exists(settings_path):
            import shutil
            shutil.copy(settings_path, settings_path + ".bak")

        with open(settings_path, "w") as f:
            json.dump(settings, f, indent=4)

        return {"status": "success", "message": "Settings updated successfully", "settings": settings}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update settings: {str(e)}")

# Order management
@router.get("/orders/all")
def get_all_orders_admin(
    status_filter: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    carrier: Optional[str] = None,
    search: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """Get all orders with advanced filtering for admin"""
    query = db.query(Order)

    # Status filter
    if status_filter:
        try:
            status_enum = OrderStatus(status_filter)
            query = query.filter(Order.status == status_enum)
        except ValueError:
            pass

    # Date range filter
    if date_from:
        try:
            from_date = datetime.fromisoformat(date_from)
            query = query.filter(Order.created_at >= from_date)
        except ValueError:
            pass

    if date_to:
        try:
            to_date = datetime.fromisoformat(date_to)
            query = query.filter(Order.created_at <= to_date)
        except ValueError:
            pass

    # Carrier filter
    if carrier:
        query = query.filter(Order.selected_carrier == carrier)

    # Search filter (order number, recipient name, contact)
    if search:
        search_pattern = f"%{search}%"
        query = query.filter(
            (Order.order_number.like(search_pattern)) |
            (Order.recipient_name.like(search_pattern)) |
            (Order.recipient_contact.like(search_pattern))
        )

    total = query.count()
    orders = query.order_by(Order.created_at.desc()).offset(skip).limit(limit).all()

    return {
        "total": total,
        "orders": orders,
        "page": skip // limit + 1,
        "page_size": limit
    }

@router.put("/orders/{order_id}")
def admin_update_order(order_id: int, order_update: OrderUpdate, db: Session = Depends(get_db)):
    """Admin can update any order field including status"""
    db_order = db.query(Order).filter(Order.id == order_id).first()

    if not db_order:
        raise HTTPException(status_code=404, detail="Order not found")

    update_data = order_update.model_dump(exclude_unset=True)

    for field, value in update_data.items():
        if field == "payment_mode" and value:
            setattr(db_order, field, PaymentMode(value))
        elif field == "status" and value:
            setattr(db_order, field, OrderStatus(value))
        else:
            setattr(db_order, field, value)

    db_order.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(db_order)

    return db_order

@router.delete("/orders/{order_id}")
def admin_delete_order(order_id: int, db: Session = Depends(get_db)):
    """Admin can delete any order"""
    db_order = db.query(Order).filter(Order.id == order_id).first()

    if not db_order:
        raise HTTPException(status_code=404, detail="Order not found")

    db.delete(db_order)
    db.commit()

    return {"status": "success", "message": f"Order {db_order.order_number} deleted"}

@router.post("/orders/bulk-update-status")
def bulk_update_status(order_ids: List[int], new_status: str, db: Session = Depends(get_db)):
    """Bulk update status for multiple orders"""
    try:
        status_enum = OrderStatus(new_status)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid status: {new_status}")

    orders = db.query(Order).filter(Order.id.in_(order_ids)).all()

    if not orders:
        raise HTTPException(status_code=404, detail="No orders found")

    for order in orders:
        order.status = status_enum
        order.updated_at = datetime.utcnow()

    db.commit()

    return {
        "status": "success",
        "message": f"{len(orders)} orders updated to {new_status}",
        "updated_orders": [order.order_number for order in orders]
    }

# Analytics & Reports
@router.get("/analytics/overview")
def get_analytics_overview(
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Get analytics overview with revenue, profit, order stats, etc."""
    query = db.query(Order)

    # Date range filter
    if date_from:
        from_date = datetime.fromisoformat(date_from)
        query = query.filter(Order.created_at >= from_date)

    if date_to:
        to_date = datetime.fromisoformat(date_to)
        query = query.filter(Order.created_at <= to_date)

    all_orders = query.all()

    # Load settings for profit calculation
    settings_path = os.path.join(os.path.dirname(__file__), "config", "settings.json")
    with open(settings_path, "r") as f:
        settings = json.load(f)

    escalation_rate = settings.get("ESCALATION_RATE", 0.15)
    gst_rate = settings.get("GST_RATE", 0.18)

    # Calculate stats
    total_orders = len(all_orders)
    booked_orders = [o for o in all_orders if o.status == OrderStatus.BOOKED]
    total_revenue = sum(o.total_cost for o in booked_orders if o.total_cost)

    # Calculate profit breakdown
    multiplier = (1 + escalation_rate) * (1 + gst_rate)
    total_base_cost = 0
    total_profit = 0
    total_gst = 0

    for order in booked_orders:
        if order.total_cost:
            base_cost = order.total_cost / multiplier
            escalation_amount = base_cost * escalation_rate
            after_escalation = base_cost + escalation_amount
            gst_amount = after_escalation * gst_rate

            total_base_cost += base_cost
            total_profit += escalation_amount
            total_gst += gst_amount

    # Orders by status
    status_breakdown = {}
    for status in OrderStatus:
        status_breakdown[status.value] = len([o for o in all_orders if o.status == status])

    # Revenue by carrier
    carrier_revenue = {}
    for order in booked_orders:
        if order.selected_carrier and order.total_cost:
            carrier_revenue[order.selected_carrier] = carrier_revenue.get(order.selected_carrier, 0) + order.total_cost

    # Orders by payment mode
    cod_orders = len([o for o in all_orders if o.payment_mode == PaymentMode.COD])
    prepaid_orders = len([o for o in all_orders if o.payment_mode == PaymentMode.PREPAID])

    return {
        "total_orders": total_orders,
        "booked_orders": len(booked_orders),
        "total_revenue": round(total_revenue, 2),
        "total_base_cost": round(total_base_cost, 2),
        "total_profit": round(total_profit, 2),
        "total_gst": round(total_gst, 2),
        "profit_margin_percent": round((total_profit / total_revenue * 100) if total_revenue > 0 else 0, 2),
        "status_breakdown": status_breakdown,
        "carrier_revenue": {k: round(v, 2) for k, v in sorted(carrier_revenue.items(), key=lambda x: x[1], reverse=True)},
        "payment_modes": {
            "cod": cod_orders,
            "prepaid": prepaid_orders
        }
    }

@router.get("/analytics/daily-stats")
def get_daily_stats(days: int = 30, db: Session = Depends(get_db)):
    """Get daily order and revenue stats for the last N days"""
    start_date = datetime.utcnow() - timedelta(days=days)

    orders = db.query(Order).filter(Order.created_at >= start_date).all()

    # Group by date
    daily_stats = {}
    for order in orders:
        date_key = order.created_at.date().isoformat()
        if date_key not in daily_stats:
            daily_stats[date_key] = {"orders": 0, "revenue": 0, "booked": 0}

        daily_stats[date_key]["orders"] += 1
        if order.status == OrderStatus.BOOKED and order.total_cost:
            daily_stats[date_key]["revenue"] += order.total_cost
            daily_stats[date_key]["booked"] += 1

    # Sort by date
    sorted_stats = sorted(daily_stats.items(), key=lambda x: x[0])

    return {
        "period_days": days,
        "data": [
            {
                "date": date,
                "orders": stats["orders"],
                "revenue": round(stats["revenue"], 2),
                "booked_orders": stats["booked"]
            }
            for date, stats in sorted_stats
        ]
    }

@router.get("/analytics/carrier-performance")
def get_carrier_performance(db: Session = Depends(get_db)):
    """Get carrier-wise performance metrics with profit breakdown"""
    booked_orders = db.query(Order).filter(Order.status == OrderStatus.BOOKED).all()

    # Load settings for escalation and GST rates
    settings_path = os.path.join(os.path.dirname(__file__), "config", "settings.json")
    with open(settings_path, "r") as f:
        settings = json.load(f)

    escalation_rate = settings.get("ESCALATION_RATE", 0.15)
    gst_rate = settings.get("GST_RATE", 0.18)

    carrier_stats = {}
    for order in booked_orders:
        if not order.selected_carrier:
            continue

        if order.selected_carrier not in carrier_stats:
            carrier_stats[order.selected_carrier] = {
                "total_orders": 0,
                "total_revenue": 0,
                "total_base_cost": 0,  # Cost before escalation
                "total_profit": 0,     # Escalation amount (profit)
                "total_gst": 0,        # GST amount
                "modes": {"Surface": 0, "Air": 0},
                "average_weight": 0,
                "total_weight": 0
            }

        stats = carrier_stats[order.selected_carrier]
        stats["total_orders"] += 1

        # Calculate breakdown from total_cost
        if order.total_cost:
            # Reverse calculation: total_cost = base * (1 + escalation) * (1 + gst)
            # base = total_cost / ((1 + escalation) * (1 + gst))
            multiplier = (1 + escalation_rate) * (1 + gst_rate)
            base_cost = order.total_cost / multiplier
            escalation_amount = base_cost * escalation_rate
            after_escalation = base_cost + escalation_amount
            gst_amount = after_escalation * gst_rate

            stats["total_revenue"] += order.total_cost
            stats["total_base_cost"] += base_cost
            stats["total_profit"] += escalation_amount
            stats["total_gst"] += gst_amount

        stats["total_weight"] += order.applicable_weight or order.weight

        if order.mode:
            stats["modes"][order.mode] = stats["modes"].get(order.mode, 0) + 1

    # Calculate averages and round
    for carrier, stats in carrier_stats.items():
        if stats["total_orders"] > 0:
            stats["average_weight"] = round(stats["total_weight"] / stats["total_orders"], 2)
            stats["average_revenue_per_order"] = round(stats["total_revenue"] / stats["total_orders"], 2)
            stats["average_profit_per_order"] = round(stats["total_profit"] / stats["total_orders"], 2)

        stats["total_revenue"] = round(stats["total_revenue"], 2)
        stats["total_base_cost"] = round(stats["total_base_cost"], 2)
        stats["total_profit"] = round(stats["total_profit"], 2)
        stats["total_gst"] = round(stats["total_gst"], 2)
        stats["profit_margin_percent"] = round((stats["total_profit"] / stats["total_revenue"] * 100) if stats["total_revenue"] > 0 else 0, 2)

        del stats["total_weight"]  # Remove internal calculation field

    # Sort by revenue
    sorted_carriers = sorted(carrier_stats.items(), key=lambda x: x[1]["total_revenue"], reverse=True)

    return {
        "carriers": [
            {"carrier": carrier, **stats}
            for carrier, stats in sorted_carriers
        ]
    }

@router.get("/analytics/zone-distribution")
def get_zone_distribution(db: Session = Depends(get_db)):
    """Get distribution of orders across zones"""
    booked_orders = db.query(Order).filter(Order.status == OrderStatus.BOOKED).all()

    zone_stats = {}
    for order in booked_orders:
        if not order.zone_applied:
            continue

        zone = order.zone_applied
        if zone not in zone_stats:
            zone_stats[zone] = {"orders": 0, "revenue": 0}

        zone_stats[zone]["orders"] += 1
        zone_stats[zone]["revenue"] += order.total_cost or 0

    # Round revenue
    for zone, stats in zone_stats.items():
        stats["revenue"] = round(stats["revenue"], 2)

    return {"zones": zone_stats}

# Carrier activation/deactivation
@router.put("/carriers/{carrier_name}/toggle-active")
def toggle_carrier_active(carrier_name: str, active: bool):
    """Activate or deactivate a carrier"""
    rate_card_path = os.path.join(os.path.dirname(__file__), "data", "rate_cards.json")

    try:
        with open(rate_card_path, "r") as f:
            carriers = json.load(f)

        carrier_found = False
        for carrier in carriers:
            if carrier.get("carrier_name") == carrier_name:
                carrier["active"] = active
                carrier_found = True
                break

        if not carrier_found:
            raise HTTPException(status_code=404, detail=f"Carrier '{carrier_name}' not found")

        # Backup and save
        import shutil
        shutil.copy(rate_card_path, rate_card_path + ".bak")

        with open(rate_card_path, "w") as f:
            json.dump(carriers, f, indent=4)

        status_text = "activated" if active else "deactivated"
        return {
            "status": "success",
            "message": f"Carrier '{carrier_name}' {status_text}",
            "carrier_name": carrier_name,
            "active": active
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update carrier: {str(e)}")

@router.delete("/carriers/{carrier_name}")
def delete_carrier(carrier_name: str):
    """Delete a carrier from rate cards"""
    rate_card_path = os.path.join(os.path.dirname(__file__), "data", "rate_cards.json")

    try:
        with open(rate_card_path, "r") as f:
            carriers = json.load(f)

        original_count = len(carriers)
        carriers = [c for c in carriers if c.get("carrier_name") != carrier_name]

        if len(carriers) == original_count:
            raise HTTPException(status_code=404, detail=f"Carrier '{carrier_name}' not found")

        # Backup and save
        import shutil
        shutil.copy(rate_card_path, rate_card_path + ".bak")

        with open(rate_card_path, "w") as f:
            json.dump(carriers, f, indent=4)

        return {
            "status": "success",
            "message": f"Carrier '{carrier_name}' deleted",
            "remaining_carriers": len(carriers)
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete carrier: {str(e)}")
