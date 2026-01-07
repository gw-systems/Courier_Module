"""
Base utilities and shared imports for views.
Contains shared functions and configuration.
"""
from rest_framework import viewsets, status
from rest_framework.decorators import api_view, action, permission_classes, throttle_classes
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from rest_framework.throttling import AnonRateThrottle
from django.conf import settings
from django.utils import timezone
from django.core.cache import cache
import json
import os
import shutil
import logging

from courier.serializers import (
    OrderSerializer, OrderUpdateSerializer, RateRequestSerializer,
    CarrierSelectionSerializer, NewCarrierSerializer, FTLOrderSerializer,
    FTLRateRequestSerializer
)
from courier.permissions import IsAdminToken

from courier.engine import calculate_cost
from courier.zones import get_zone_column, PINCODE_LOOKUP
from courier.models import Order, OrderStatus, PaymentMode, FTLOrder, Courier, SystemConfig


logger = logging.getLogger('courier')

# Path configurations
BASE_DIR = settings.BASE_DIR
RATE_CARD_PATH = os.path.join(BASE_DIR, "courier", "data", "master_card.json")
FTL_RATES_PATH = os.path.join(BASE_DIR, "courier", "data", "ftl_rates.json")


def load_rates():
    """
    Load rate cards with caching for performance.
    Cache timeout: 5 minutes (300 seconds).
    """
    CACHE_KEY = 'carrier_rate_cards'
    CACHE_TIMEOUT = 300  # 5 minutes
    
    # Try to get from cache first
    rates = cache.get(CACHE_KEY)
    if rates is not None:
        return rates
    
    # Cache miss - load from DB
    try:
        couriers = Courier.objects.filter(is_active=True).prefetch_related(
            'city_routes', 'delivery_slabs', 'custom_zones', 'custom_zone_rates'
        )
        rates = [c.get_rate_dict() for c in couriers]
        
        if not rates:
            logger.warning("No active couriers found in database")
            
        # Store in cache
        cache.set(CACHE_KEY, rates, CACHE_TIMEOUT)
        logger.info(f"Rate cards loaded from DB and cached ({len(rates)} carriers)")
        return rates

    except Exception as e:
        logger.error(f"Unexpected error loading rate cards from DB: {e}")
        return []


def load_ftl_rates():
    """
    Load FTL rates from JSON file with caching.
    Cache timeout: 5 minutes (300 seconds).
    """
    CACHE_KEY = 'ftl_rate_cards'
    CACHE_TIMEOUT = 300  # 5 minutes
    
    # Try to get from cache first
    rates = cache.get(CACHE_KEY)
    if rates is not None:
        return rates
    
    # Cache miss - load from file
    try:
        if not os.path.exists(FTL_RATES_PATH):
            logger.warning(f"FTL rates file not found at {FTL_RATES_PATH}")
            return {}
        
        with open(FTL_RATES_PATH, "r") as f:
            rates = json.load(f)
        
        # Store in cache
        cache.set(CACHE_KEY, rates, CACHE_TIMEOUT)
        logger.info("FTL rates loaded and cached")
        return rates
        
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in FTL rates file: {e}")
        return {}
    except Exception as e:
        logger.error(f"Error loading FTL rates: {e}")
        return {}


def invalidate_rates_cache():
    """
    Invalidate all rate-related caches.
    Call this after updating rate cards via admin endpoints.
    """
    cache.delete('carrier_rate_cards')
    cache.delete('ftl_rate_cards')
    logger.info("Rate card caches invalidated")


def generate_order_number():
    """Generate unique order number"""
    today = timezone.now()
    prefix = f"ORD-{today.year}-"

    # Get the latest order number for today
    latest_order = (
        Order.objects
        .filter(order_number__startswith=prefix)
        .order_by('-id')
        .first()
    )

    if latest_order:
        try:
            last_num = int(latest_order.order_number.split("-")[-1])
            new_num = last_num + 1
        except (ValueError, IndexError):
            new_num = 1001
    else:
        new_num = 1001

    return f"{prefix}{new_num}"


def generate_ftl_order_number():
    """Generate unique FTL order number"""
    today = timezone.now()
    prefix = f"FTL-{today.year}-"

    # Get the latest FTL order number for today
    latest_order = (
        FTLOrder.objects
        .filter(order_number__startswith=prefix)
        .order_by('-id')
        .first()
    )

    if latest_order:
        try:
            last_num = int(latest_order.order_number.split("-")[-1])
            new_num = last_num + 1
        except (ValueError, IndexError):
            new_num = 1001
    else:
        new_num = 1001

    return f"{prefix}{new_num}"


def calculate_ftl_price(base_price):
    """Calculate FTL price with escalation and GST
    Formula: base_price + escalation, then add GST
    Uses rates from global settings.
    """
    conf = SystemConfig.get_solo()
    ESCALATION_RATE = float(conf.escalation_rate)
    GST_RATE = float(conf.gst_rate)
    
    escalation_amount = base_price * ESCALATION_RATE
    price_with_escalation = base_price + escalation_amount
    gst_amount = price_with_escalation * GST_RATE
    total_price = price_with_escalation + gst_amount
    
    return {
        "base_price": round(base_price, 2),
        "escalation_amount": round(escalation_amount, 2),
        "price_with_escalation": round(price_with_escalation, 2),
        "gst_amount": round(gst_amount, 2),
        "total_price": round(total_price, 2)
    }
