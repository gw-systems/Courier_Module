"""
Public API Views.
Contains health check, rate comparison, and pincode lookup endpoints.
"""
from rest_framework.decorators import api_view, permission_classes, throttle_classes
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from rest_framework.throttling import AnonRateThrottle
from rest_framework import status
from django.shortcuts import render, redirect

from .base import (
    load_rates, logger, RateRequestSerializer,
    get_zone_column, PINCODE_LOOKUP, calculate_cost
)
from django.conf import settings
from courier.serializers import RateRequestSerializer
from courier.engine import calculate_cost
from courier.zones import get_zone_column, PINCODE_LOOKUP


@api_view(['GET'])
@permission_classes([AllowAny])
def health_check(request):
    """Health check endpoint for monitoring"""
    return Response({
        "status": "healthy",
        "pincode_db_loaded": len(PINCODE_LOOKUP) > 0,
        "pincode_count": len(PINCODE_LOOKUP),
        "rate_cards_loaded": len(load_rates()) > 0,
        "rate_card_count": len(load_rates())
    })


def dashboard_view(request):
    """Render the main dashboard (Django template)"""
    return render(request, 'dashboard.html', {'section': 'dashboard'})


def rate_calculator_view(request):
    """Render the dashboard with rate calculator active by default"""
    return render(request, 'dashboard.html', {'section': 'rate-calculator'})


@api_view(['GET'])
@permission_classes([AllowAny])
def root_redirect(request):
    """Redirect to dashboard"""
    return redirect('/dashboard/')


@api_view(['POST'])
@throttle_classes([AnonRateThrottle])
@permission_classes([AllowAny])
def compare_rates(request):
    """Compare shipping rates across carriers"""
    serializer = RateRequestSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    data = serializer.validated_data

    zone_key, zone_label = get_zone_column(
        data['source_pincode'],
        data['dest_pincode']
    )

    # Calculate Total Weight
    if data.get('orders'):
        # Multi-box logic
        try:
            # Load Volumetric Divisor from Config
            vol_divisor = settings.COURIER_BUSINESS_RULES.get('VOLUMETRIC_DIVISOR', 5000)
        except Exception:
            vol_divisor = 5000 # Fallback

        total_weight = 0
        for box in data['orders']:
            vol_weight = (box['length'] * box['width'] * box['height']) / vol_divisor
            applicable = max(box['weight'], vol_weight)
            total_weight += applicable
    else:
        # Legacy single weight logic
        total_weight = data['weight']

    rates = load_rates()
    results = []

    for carrier in rates:
        if not carrier.get("active", True):
            continue

        req_mode = data['mode'].lower()
        car_mode = carrier.get("mode", "Surface").lower()
        if req_mode != "both" and car_mode != req_mode:
            continue

        try:
            res = calculate_cost(
                weight=total_weight,
                source_pincode=data['source_pincode'],
                dest_pincode=data['dest_pincode'],
                carrier_data=carrier,
                is_cod=data['is_cod'],
                order_value=data['order_value']
            )

            res["applied_zone"] = res.get("zone", "") # Use zone from engine result
            res["mode"] = carrier.get("mode", "Surface")
            results.append(res)
        except Exception as e:
            logger.error(f"CALCULATION_ERROR: Carrier {carrier.get('carrier_name')} failed. Error: {str(e)}")
            continue

    # Filter out non-servicable carriers before sorting
    valid_results = [r for r in results if r.get("servicable")]

    if not valid_results:
        logger.warning(f"No serviceable carriers matched for mode: {data['mode']}")
        return Response(
            {"detail": f"No serviceable carriers found for this route."},
            status=status.HTTP_404_NOT_FOUND
        )

    return Response(sorted(valid_results, key=lambda x: x["total_cost"]))


@api_view(['GET'])
@permission_classes([AllowAny])
def lookup_pincode(request, pincode):
    """Get city and state for a pincode"""
    pincode_data = PINCODE_LOOKUP.get(int(pincode))

    if not pincode_data:
        return Response(
            {"detail": "Pincode not found"},
            status=status.HTTP_404_NOT_FOUND
        )

    return Response({
        "pincode": pincode,
        "city": pincode_data.get("district", ""),
        "state": pincode_data.get("state", ""),
        "office": pincode_data.get("office", "")
    })
