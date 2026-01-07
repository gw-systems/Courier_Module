"""
Admin Views.
Contains admin endpoints for rate card management.
"""
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework import status
import json
import os
import shutil

from courier.permissions import IsAdminToken
from courier.serializers import NewCarrierSerializer, OrderSerializer, FTLOrderSerializer
from courier.models import Order, FTLOrder
from .base import (
    load_rates, invalidate_rates_cache, logger,
    RATE_CARD_PATH
)


@api_view(['GET'])
@permission_classes([IsAdminToken])
def get_all_rates(request):
    """Get all carrier rates"""
    with open(RATE_CARD_PATH, "r") as f:
        return Response(json.load(f))


@api_view(['POST'])
@permission_classes([IsAdminToken])
def update_rates(request):
    """Update carrier rates"""
    try:
        new_data = request.data

        if os.path.exists(RATE_CARD_PATH):
            shutil.copy(RATE_CARD_PATH, RATE_CARD_PATH + ".bak")

        with open(RATE_CARD_PATH, "w") as f:
            json.dump(new_data, f, indent=4)

        logger.info("ADMIN_ACTION: Rates updated successfully.")
        invalidate_rates_cache()  # Clear cache after update
        return Response({"status": "success", "message": "Rates updated successfully"})
    except Exception as e:
        logger.error(f"ADMIN_ERROR: Failed to update rates: {str(e)}")
        return Response(
            {"detail": f"Failed to update rates: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([IsAdminToken])
def add_carrier(request):
    """Add a new carrier to the rate cards"""
    serializer = NewCarrierSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    carrier_data = serializer.validated_data

    try:
        # Load existing rates
        existing_rates = load_rates()

        # Check for duplicate carrier name
        carrier_names = [c.get("carrier_name", "").lower() for c in existing_rates]
        if carrier_data['carrier_name'].lower() in carrier_names:
            logger.warning(f"ADMIN_ACTION: Duplicate carrier name attempted: {carrier_data['carrier_name']}")
            return Response(
                {"detail": f"Carrier '{carrier_data['carrier_name']}' already exists."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Append new carrier
        existing_rates.append(carrier_data)

        # Backup and save
        if os.path.exists(RATE_CARD_PATH):
            shutil.copy(RATE_CARD_PATH, RATE_CARD_PATH + ".bak")

        with open(RATE_CARD_PATH, "w") as f:
            json.dump(existing_rates, f, indent=4)

        logger.info(f"ADMIN_ACTION: New carrier added: {carrier_data['carrier_name']}")
        invalidate_rates_cache()  # Clear cache after update
        return Response({
            "status": "success",
            "message": f"Carrier '{carrier_data['carrier_name']}' added successfully",
            "carrier": carrier_data
        }, status=status.HTTP_201_CREATED)

    except Exception as e:
        logger.error(f"ADMIN_ERROR: Failed to add carrier: {str(e)}")
        return Response(
            {"detail": f"Failed to add carrier: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['PUT'])
@permission_classes([IsAdminToken])
def toggle_carrier_active(request, carrier_name):
    """Toggle carrier active/inactive status"""
    active = request.data.get('active')

    if active is None:
        return Response(
            {"detail": "Missing 'active' parameter"},
            status=status.HTTP_400_BAD_REQUEST
        )

    try:
        # Load existing rates
        carriers = load_rates()

        # Find and update the carrier
        carrier_found = False
        for carrier in carriers:
            if carrier.get("carrier_name") == carrier_name:
                carrier["active"] = active
                carrier_found = True
                break

        if not carrier_found:
            return Response(
                {"detail": f"Carrier '{carrier_name}' not found"},
                status=status.HTTP_404_NOT_FOUND
            )

        # Backup and save
        if os.path.exists(RATE_CARD_PATH):
            shutil.copy(RATE_CARD_PATH, RATE_CARD_PATH + ".bak")

        with open(RATE_CARD_PATH, "w") as f:
            json.dump(carriers, f, indent=4)

        logger.info(f"ADMIN_ACTION: Carrier '{carrier_name}' {'activated' if active else 'deactivated'}")
        invalidate_rates_cache()  # Clear cache after update
        return Response({
            "status": "success",
            "message": f"Carrier '{carrier_name}' {'activated' if active else 'deactivated'}",
            "carrier_name": carrier_name,
            "active": active
        })

    except Exception as e:
        logger.error(f"ADMIN_ERROR: Failed to toggle carrier status: {str(e)}")
        return Response(
            {"detail": f"Failed to toggle carrier status: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['DELETE'])
@permission_classes([IsAdminToken])
def delete_carrier(request, carrier_name):
    """Delete a carrier from rate cards"""
    try:
        # Load existing rates
        carriers = load_rates()

        # Filter out the carrier
        initial_count = len(carriers)
        carriers = [c for c in carriers if c.get("carrier_name") != carrier_name]

        if len(carriers) == initial_count:
            return Response(
                {"detail": f"Carrier '{carrier_name}' not found"},
                status=status.HTTP_404_NOT_FOUND
            )

        # Backup and save
        if os.path.exists(RATE_CARD_PATH):
            shutil.copy(RATE_CARD_PATH, RATE_CARD_PATH + ".bak")

        with open(RATE_CARD_PATH, "w") as f:
            json.dump(carriers, f, indent=4)

        logger.info(f"ADMIN_ACTION: Carrier '{carrier_name}' deleted")
        invalidate_rates_cache()  # Clear cache after update
        return Response({
            "status": "success",
            "message": f"Carrier '{carrier_name}' deleted successfully",
            "remaining_carriers": len(carriers)
        })

    except Exception as e:
        logger.error(f"ADMIN_ERROR: Failed to delete carrier: {str(e)}")
        return Response(
            {"detail": f"Failed to delete carrier: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['PATCH'])
@permission_classes([IsAdminToken])
def update_carrier(request, carrier_name):
    """Update carrier details"""
    try:
        # Load existing rates
        carriers = load_rates()

        # Find the carrier
        carrier_found = False
        carrier_index = None
        for i, carrier in enumerate(carriers):
            if carrier.get("carrier_name") == carrier_name:
                carrier_found = True
                carrier_index = i
                break

        if not carrier_found:
            return Response(
                {"detail": f"Carrier '{carrier_name}' not found"},
                status=status.HTTP_404_NOT_FOUND
            )

        # Validate the update data with serializer (partial update)
        serializer = NewCarrierSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        update_data = serializer.validated_data

        # Update the carrier
        carriers[carrier_index].update(update_data)

        # Backup and save
        if os.path.exists(RATE_CARD_PATH):
            shutil.copy(RATE_CARD_PATH, RATE_CARD_PATH + ".bak")

        with open(RATE_CARD_PATH, "w") as f:
            json.dump(carriers, f, indent=4)

        logger.info(f"ADMIN_ACTION: Carrier '{carrier_name}' updated")
        invalidate_rates_cache()  # Clear cache after update
        return Response({
            "status": "success",
            "message": f"Carrier '{carrier_name}' updated successfully",
            "carrier": carriers[carrier_index]
        })

    except Exception as e:
        logger.error(f"ADMIN_ERROR: Failed to update carrier: {str(e)}")
        return Response(
            {"detail": f"Failed to update carrier: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAdminToken])
def admin_orders_list(request):
    """Get all orders for admin dashboard with filtering"""
    from courier.models import Order
    from courier.serializers import OrderSerializer
    from django.db.models import Sum, Count

    # Get query params
    status_filter = request.query_params.get('status')
    carrier_filter = request.query_params.get('carrier')
    limit = int(request.query_params.get('limit', 100))

    # Build queryset
    queryset = Order.objects.all().order_by('-created_at')

    if status_filter:
        queryset = queryset.filter(status=status_filter)
    if carrier_filter:
        queryset = queryset.filter(carrier__name=carrier_filter)

    # Get orders
    orders = queryset[:limit]

    return Response({
        "count": queryset.count(),
        "orders": OrderSerializer(orders, many=True).data
    })


@api_view(['GET'])
@permission_classes([IsAdminToken])
def admin_ftl_orders_list(request):
    """Get all FTL orders for admin dashboard"""
    from courier.models import FTLOrder
    from courier.serializers import FTLOrderSerializer

    # Get query params
    status_filter = request.query_params.get('status')
    limit = int(request.query_params.get('limit', 100))

    # Build queryset
    queryset = FTLOrder.objects.all().order_by('-created_at')

    if status_filter:
        queryset = queryset.filter(status=status_filter)

    # Get orders
    orders = queryset[:limit]

    return Response({
        "count": queryset.count(),
        "orders": FTLOrderSerializer(orders, many=True).data
    })


@api_view(['GET'])
@permission_classes([IsAdminToken])
def admin_dashboard_stats(request):
    """Get dashboard statistics for admin"""
    from courier.models import Order, FTLOrder, OrderStatus
    from django.db.models import Sum, Count
    from django.utils import timezone
    from datetime import timedelta

    today = timezone.now().date()
    last_30_days = today - timedelta(days=30)

    # Order stats
    order_stats = Order.objects.aggregate(
        total_orders=Count('id'),
        total_revenue=Sum('total_cost'),
    )

    # Orders by status
    status_counts = Order.objects.values('status').annotate(
        count=Count('id')
    ).order_by('status')

    # Carrier performance
    carrier_stats = Order.objects.exclude(
        carrier__isnull=True
    ).values('carrier__name').annotate(
        order_count=Count('id'),
        revenue=Sum('total_cost')
    ).order_by('-order_count')[:10]

    # FTL stats
    ftl_stats = FTLOrder.objects.aggregate(
        total_orders=Count('id'),
        total_revenue=Sum('total_price'),
    )

    # Recent activity (last 30 days)
    recent_orders = Order.objects.filter(
        created_at__date__gte=last_30_days
    ).count()

    recent_booked = Order.objects.filter(
        status=OrderStatus.BOOKED,
        booked_at__date__gte=last_30_days
    ).count()

    # Active carriers
    carriers = load_rates()
    active_carriers = len([c for c in carriers if c.get('active', True)])
    total_carriers = len(carriers)

    return Response({
        "orders": {
            "total": order_stats['total_orders'] or 0,
            "total_revenue": float(order_stats['total_revenue'] or 0),
            "by_status": {item['status']: item['count'] for item in status_counts},
            "recent_30_days": recent_orders,
            "booked_30_days": recent_booked,
        },
        "ftl_orders": {
            "total": ftl_stats['total_orders'] or 0,
            "total_revenue": float(ftl_stats['total_revenue'] or 0),
        },
        "carriers": {
            "total": total_carriers,
            "active": active_carriers,
            "inactive": total_carriers - active_carriers,
            "performance": list(carrier_stats),
        },
        "generated_at": timezone.now().isoformat(),
    })
