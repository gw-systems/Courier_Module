"""
Public API Views.
Contains health check, rate comparison, and pincode lookup endpoints.
"""
from rest_framework.decorators import api_view, permission_classes, throttle_classes
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from rest_framework.throttling import AnonRateThrottle
from rest_framework import status
from django.shortcuts import redirect

from .base import (
    load_rates, logger, RateRequestSerializer,
    get_zone_column, PINCODE_LOOKUP, calculate_cost
)
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


@api_view(['GET'])
@permission_classes([AllowAny])
def root_redirect(request):
    """Redirect to dashboard"""
    return redirect('/static/dashboard.html')


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
                weight=data['weight'],
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

    if not results:
        logger.warning(f"No carriers matched for mode: {data['mode']}")
        return Response(
            {"detail": f"No active carriers found for mode '{data['mode']}'."},
            status=status.HTTP_404_NOT_FOUND
        )

    return Response(sorted(results, key=lambda x: x["total_cost"]))


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
