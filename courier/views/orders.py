"""
Order Management Views.
Contains OrderViewSet for CRUD operations on orders.
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from django.utils import timezone

from courier.models import Order, OrderStatus, PaymentMode
from courier.serializers import (
    OrderSerializer, OrderUpdateSerializer, CarrierSelectionSerializer
)
from courier.engine import calculate_cost
from .base import load_rates, generate_order_number


class OrderViewSet(viewsets.ModelViewSet):
    """Order management ViewSet"""
    queryset = Order.objects.all()
    serializer_class = OrderSerializer
    permission_classes = [AllowAny]

    def get_serializer_class(self):
        if self.action == 'partial_update' or self.action == 'update':
            return OrderUpdateSerializer
        return OrderSerializer

    def get_queryset(self):
        queryset = Order.objects.all()
        status_param = self.request.query_params.get('status')

        if status_param:
            try:
                queryset = queryset.filter(status=status_param)
            except ValueError:
                pass

        return queryset.order_by('-created_at')

    def create(self, request, *args, **kwargs):
        """Create a new order"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # Generate order number
        order_number = generate_order_number()

        # Create order
        order = serializer.save(
            order_number=order_number,
            status=OrderStatus.DRAFT
        )

        return Response(
            OrderSerializer(order).data,
            status=status.HTTP_201_CREATED
        )

    def update(self, request, *args, **kwargs):
        """Update an order - only allowed for DRAFT orders"""
        order = self.get_object()

        # Only DRAFT orders can be edited
        if order.status != OrderStatus.DRAFT:
            return Response(
                {"detail": "You can only edit orders in DRAFT status"},
                status=status.HTTP_403_FORBIDDEN
            )

        return super().update(request, *args, **kwargs)

    def partial_update(self, request, *args, **kwargs):
        """Partial update an order - only allowed for DRAFT orders"""
        order = self.get_object()

        # Only DRAFT orders can be edited
        if order.status != OrderStatus.DRAFT:
            return Response(
                {"detail": "You can only edit orders in DRAFT status"},
                status=status.HTTP_403_FORBIDDEN
            )

        return super().partial_update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        """Delete an order - allowed for DRAFT or CANCELLED orders"""
        order = self.get_object()

        # Only DRAFT or CANCELLED orders can be deleted
        if order.status not in [OrderStatus.DRAFT, OrderStatus.CANCELLED]:
            return Response(
                {"detail": "You can only delete orders in DRAFT or CANCELLED status"},
                status=status.HTTP_403_FORBIDDEN
            )

        order.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=False, methods=['post'], url_path='compare-carriers')
    def compare_carriers(self, request):
        """Compare carrier rates for one or more orders"""
        order_ids = request.data.get('order_ids', [])

        if not order_ids:
            return Response(
                {"detail": "No orders provided"},
                status=status.HTTP_400_BAD_REQUEST
            )

        orders = Order.objects.filter(id__in=order_ids)

        if orders.count() != len(order_ids):
            return Response(
                {"detail": "One or more orders not found"},
                status=status.HTTP_404_NOT_FOUND
            )

        # Aggregate weights and use first order's pincodes
        total_weight = sum(order.applicable_weight or order.weight for order in orders)
        first_order = orders.first()
        source_pincode = first_order.sender_pincode
        dest_pincode = first_order.recipient_pincode

        # Check if COD
        is_cod = any(order.payment_mode == PaymentMode.COD for order in orders)
        total_order_value = sum(
            order.order_value for order in orders
            if order.payment_mode == PaymentMode.COD
        )

        # Load carriers (zone logic is now handled inside calculate_cost)
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

                # Skip if not serviceable
                if res.get("servicable") == False:
                    continue

                res["mode"] = carrier.get("mode", "Surface")
                res["applied_zone"] = res.get("zone", "")  # Map zone to applied_zone for frontend
                res["order_count"] = len(order_ids)
                res["total_weight"] = total_weight
                results.append(res)

            except Exception as e:
                import logging
                logging.getLogger('courier').warning(f"Carrier {carrier.get('carrier_name')} failed: {e}")
                continue

        if not results:
            return Response(
                {"detail": "No active carriers found"},
                status=status.HTTP_404_NOT_FOUND
            )

        return Response({
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
        })

    @action(detail=False, methods=['post'], url_path='book-carrier')
    def book_carrier(self, request):
        """Book a carrier for selected orders"""
        serializer = CarrierSelectionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        orders = Order.objects.filter(id__in=data['order_ids'])

        if orders.count() != len(data['order_ids']):
            return Response(
                {"detail": "One or more orders not found"},
                status=status.HTTP_404_NOT_FOUND
            )

        # Calculate rates
        total_weight = sum(order.applicable_weight or order.weight for order in orders)
        first_order = orders.first()
        source_pincode = first_order.sender_pincode
        dest_pincode = first_order.recipient_pincode
        is_cod = any(order.payment_mode == PaymentMode.COD for order in orders)
        total_order_value = sum(
            order.order_value for order in orders
            if order.payment_mode == PaymentMode.COD
        )

        # Find the carrier
        rates = load_rates()
        carrier_data = None
        for carrier in rates:
            if (carrier.get("carrier_name") == data['carrier_name'] and
                    carrier.get("mode") == data['mode']):
                carrier_data = carrier
                break

        if not carrier_data:
            return Response(
                {"detail": "Carrier not found"},
                status=status.HTTP_404_NOT_FOUND
            )

        # Calculate cost using refactored engine
        cost_result = calculate_cost(
            weight=total_weight,
            source_pincode=source_pincode,
            dest_pincode=dest_pincode,
            carrier_data=carrier_data,
            is_cod=is_cod,
            order_value=total_order_value
        )

        # Check if serviceable
        if cost_result.get("servicable") == False:
            return Response(
                {"detail": f"Route not serviceable by {data['carrier_name']}"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Update all orders
        for order in orders:
            order.selected_carrier = data['carrier_name']
            order.mode = data['mode']
            order.zone_applied = cost_result.get("zone", "")
            order.total_cost = cost_result["total_cost"]
            order.cost_breakdown = cost_result.get("breakdown", {})
            order.status = OrderStatus.BOOKED
            order.booked_at = timezone.now()
            order.save()

        return Response({
            "status": "success",
            "message": f"{orders.count()} order(s) booked with {data['carrier_name']}",
            "orders_updated": [order.order_number for order in orders],
            "total_cost": cost_result["total_cost"],
            "carrier": data['carrier_name'],
            "mode": data['mode']
        })

    @action(detail=True, methods=['post'], url_path='cancel')
    def cancel_order(self, request, pk=None):
        """
        Cancel a booking.
        Only BOOKED orders can be cancelled (not IN_TRANSIT or later).
        """
        order = self.get_object()

        # Cannot cancel orders that are IN_TRANSIT or later
        if order.status in [OrderStatus.PICKED_UP, OrderStatus.DELIVERED]:
            return Response(
                {"detail": f"Cannot cancel order in {order.status} status. Orders in transit or delivered cannot be cancelled."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Can only cancel BOOKED orders
        if order.status != OrderStatus.BOOKED:
            return Response(
                {"detail": f"Can only cancel orders in BOOKED status. Current status: {order.status}"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Prevent cancelling already cancelled orders
        if order.status == OrderStatus.CANCELLED:
            return Response(
                {"detail": "Order is already cancelled"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Cancel the order
        previous_status = order.status
        order.status = OrderStatus.CANCELLED
        order.save()

        return Response({
            "status": "success",
            "message": f"Order {order.order_number} cancelled successfully",
            "order_number": order.order_number,
            "previous_status": previous_status,
            "current_status": order.status
        })
