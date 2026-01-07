import logging
from typing import List, Dict, Any

from django.utils import timezone
from courier.models import Order, OrderStatus, PaymentMode, Courier
from courier.engine import calculate_cost
from courier.views.base import load_rates

logger = logging.getLogger('courier')

class CarrierService:
    """Service to handle carrier rate comparisons"""
    
    @staticmethod
    def compare_rates(order_ids: List[int]) -> Dict[str, Any]:
        """
        Compare rates for a list of orders across all active couriers.

        Args:
            order_ids (List[int]): List of Order IDs to compare.

        Returns:
            Dict[str, Any]: A dictionary containing:
                - orders: QuerySet of Order objects.
                - carriers: List of dicts with cost details, sorted by total_cost.
                - source_pincode: Verified source pincode.
                - dest_pincode: Verified destination pincode.
                - total_weight: Aggregated weight of all orders.

        Raises:
            ValueError: If orders are missing or invalid.
        """
        orders = Order.objects.filter(id__in=order_ids)
        if orders.count() != len(order_ids):
            raise ValueError("One or more orders not found")

        # Aggregate inputs
        total_weight = sum(order.applicable_weight or order.weight for order in orders)
        first_order = orders.first()
        # Use simple fallback if no orders (should check earlier, but type safety)
        if not first_order:
            raise ValueError("No orders provided")
            
        source_pincode = first_order.sender_pincode
        dest_pincode = first_order.recipient_pincode

        is_cod = any(order.payment_mode == PaymentMode.COD for order in orders)
        total_order_value = sum(
            order.order_value for order in orders
            if order.payment_mode == PaymentMode.COD
        )

        rates = load_rates()
        results = []

        for carrier in rates:
            if not carrier.get("active", True):
                continue

            try:
                res = calculate_cost(
                    weight=total_weight,
                    source_pincode=source_pincode,
                    dest_pincode=dest_pincode,
                    carrier_data=carrier,
                    is_cod=is_cod,
                    order_value=total_order_value
                )

                if res.get("servicable") is False:
                    continue

                res["mode"] = carrier.get("mode", "Surface")
                res["applied_zone"] = res.get("zone", "")
                res["order_count"] = len(order_ids)
                res["total_weight"] = total_weight
                results.append(res)

            except Exception as e:
                logger.warning(f"Carrier {carrier.get('carrier_name')} failed: {e}")
                continue

        return {
            "orders": orders,
            "carriers": sorted(results, key=lambda x: x["total_cost"]),
            "source_pincode": source_pincode,
            "dest_pincode": dest_pincode,
            "total_weight": total_weight
        }


class BookingService:
    """Service to handle booking operations"""
    
    @staticmethod
    def book_orders(order_ids: List[int], carrier_name: str, mode: str) -> Dict[str, Any]:
        """
        Book a list of orders with a specific carrier.

        Args:
            order_ids (List[int]): List of Order IDs to book.
            carrier_name (str): Name of the carrier (referenced in Courier model).
            mode (str): Transport mode (e.g., 'Surface', 'Air').

        Returns:
            Dict[str, Any]: Booking result details including status and cost.

        Raises:
            ValueError: If carrier not found, route not serviceable, or orders invalid.
        """
        orders = Order.objects.filter(id__in=order_ids)
        if orders.count() != len(order_ids):
             raise ValueError("One or more orders not found")

        # Calculate cost again to ensure data integrity
        # (Alternatively we could trust the frontend, but backend calc is safer)
        total_weight = sum(order.applicable_weight or order.weight for order in orders)
        first_order = orders.first()
        source_pincode = first_order.sender_pincode
        dest_pincode = first_order.recipient_pincode
        is_cod = any(order.payment_mode == PaymentMode.COD for order in orders)
        total_order_value = sum(
            order.order_value for order in orders
            if order.payment_mode == PaymentMode.COD
        )

        # Find Carrier
        rates = load_rates()
        carrier_data = None
        for carrier in rates:
            if (carrier.get("carrier_name") == carrier_name and
                    carrier.get("mode") == mode):
                carrier_data = carrier
                break
        
        if not carrier_data:
            raise ValueError("Carrier not found")

        # Re-Calculate
        cost_result = calculate_cost(
            weight=total_weight,
            source_pincode=source_pincode,
            dest_pincode=dest_pincode,
            carrier_data=carrier_data,
            is_cod=is_cod,
            order_value=total_order_value
        )

        if cost_result.get("servicable") is False:
             raise ValueError(f"Route not serviceable by {carrier_name}")
             
        # Get Courier DB Object
        try:
            courier_obj = Courier.objects.get(name=carrier_name)
        except Courier.DoesNotExist:
            raise ValueError("Carrier object not found in DB")

        # Update Orders
        updated_numbers = []
        for order in orders:
            order.carrier = courier_obj
            order.mode = mode
            order.zone_applied = cost_result.get("zone", "")
            order.total_cost = cost_result["total_cost"]
            order.cost_breakdown = cost_result.get("breakdown", {})
            order.status = OrderStatus.BOOKED
            order.booked_at = timezone.now()
            order.save()
            updated_numbers.append(order.order_number)

        return {
            "status": "success",
            "message": f"{orders.count()} order(s) booked with {carrier_name}",
            "orders_updated": updated_numbers,
            "total_cost": cost_result["total_cost"],
            "carrier": carrier_name,
            "mode": mode
        }
