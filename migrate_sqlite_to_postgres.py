#!/usr/bin/env python
"""
SQLite to PostgreSQL Data Migration Script

This script migrates all data from the SQLite database (logistics.db)
to PostgreSQL while preserving all relationships and IDs.

Usage:
    1. Ensure PostgreSQL is running (docker-compose -f docker-compose-dev.yml up -d)
    2. Set environment variables or use defaults
    3. Run: python migrate_sqlite_to_postgres.py
"""

import os
import sys
import django
import sqlite3
from pathlib import Path

# Setup Django
BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

# Set PostgreSQL environment variables (using port 5433 for Docker container)
os.environ.setdefault('DB_NAME', 'courier_db')
os.environ.setdefault('DB_USER', 'courier_user')
os.environ.setdefault('DB_PASSWORD', 'courier_pass')
os.environ.setdefault('DB_HOST', 'localhost')
os.environ.setdefault('DB_PORT', '5433')

django.setup()

from django.db import connection
from django.core.management import call_command
from courier.models import Courier, CityRoute, CustomZone, CustomZoneRate, Order, FTLOrder
from decimal import Decimal
from datetime import datetime
import json


def get_sqlite_connection():
    """Connect to the SQLite database"""
    sqlite_path = BASE_DIR / 'logistics.db'
    if not sqlite_path.exists():
        print(f"ERROR: SQLite database not found at {sqlite_path}")
        sys.exit(1)
    return sqlite3.connect(sqlite_path)


def parse_datetime(dt_str):
    """Parse datetime string from SQLite"""
    if not dt_str:
        return None
    try:
        # Try common formats
        for fmt in ['%Y-%m-%d %H:%M:%S.%f', '%Y-%m-%d %H:%M:%S', '%Y-%m-%dT%H:%M:%S.%f', '%Y-%m-%dT%H:%M:%S']:
            try:
                return datetime.strptime(dt_str, fmt)
            except ValueError:
                continue
        return None
    except Exception:
        return None


def migrate_couriers(sqlite_conn):
    """Migrate couriers table"""
    print("\n[1/6] Migrating Couriers...")
    cursor = sqlite_conn.cursor()
    cursor.execute("SELECT * FROM couriers")
    columns = [description[0] for description in cursor.description]
    rows = cursor.fetchall()
    
    count = 0
    for row in rows:
        data = dict(zip(columns, row))
        
        # Parse JSON fields
        rate_card = data.get('rate_card', '{}')
        if isinstance(rate_card, str):
            try:
                rate_card = json.loads(rate_card)
            except:
                rate_card = {}
        
        courier = Courier(
            id=data['id'],
            name=data['name'],
            is_active=bool(data.get('is_active', True)),
            carrier_type=data.get('carrier_type', 'Courier'),
            carrier_mode=data.get('carrier_mode', 'Surface'),
            rate_logic=data.get('rate_logic', 'Zonal_Standard'),
            min_weight=float(data.get('min_weight', 0.5)),
            max_weight=float(data.get('max_weight', 99999.0)),
            volumetric_divisor=int(data.get('volumetric_divisor', 5000)),
            cod_charge_fixed=float(data.get('cod_charge_fixed', 0.0)),
            cod_charge_percent=float(data.get('cod_charge_percent', 0.0)),
            fuel_surcharge_percent=float(data.get('fuel_surcharge_percent', 0.0)),
            fwd_z_a=float(data.get('fwd_z_a', 0.0)),
            fwd_z_b=float(data.get('fwd_z_b', 0.0)),
            fwd_z_c=float(data.get('fwd_z_c', 0.0)),
            fwd_z_d=float(data.get('fwd_z_d', 0.0)),
            fwd_z_e=float(data.get('fwd_z_e', 0.0)),
            fwd_z_f=float(data.get('fwd_z_f', 0.0)),
            add_z_a=float(data.get('add_z_a', 0.0)),
            add_z_b=float(data.get('add_z_b', 0.0)),
            add_z_c=float(data.get('add_z_c', 0.0)),
            add_z_d=float(data.get('add_z_d', 0.0)),
            add_z_e=float(data.get('add_z_e', 0.0)),
            add_z_f=float(data.get('add_z_f', 0.0)),
            rate_card=rate_card,
        )
        courier.save()
        count += 1
    
    print(f"   Migrated {count} couriers")
    return count


def migrate_city_routes(sqlite_conn):
    """Migrate city_routes table"""
    print("\n[2/6] Migrating City Routes...")
    cursor = sqlite_conn.cursor()
    
    try:
        cursor.execute("SELECT * FROM city_routes")
        columns = [description[0] for description in cursor.description]
        rows = cursor.fetchall()
    except sqlite3.OperationalError:
        print("   Table city_routes not found or empty")
        return 0
    
    count = 0
    for row in rows:
        data = dict(zip(columns, row))
        CityRoute.objects.create(
            id=data['id'],
            courier_id=data['courier_id'],
            city_name=data['city_name'],
            rate_per_kg=float(data.get('rate_per_kg', 0.0)),
        )
        count += 1
    
    print(f"   Migrated {count} city routes")
    return count


def migrate_custom_zones(sqlite_conn):
    """Migrate custom_zones table"""
    print("\n[3/6] Migrating Custom Zones...")
    cursor = sqlite_conn.cursor()
    
    try:
        cursor.execute("SELECT * FROM custom_zones")
        columns = [description[0] for description in cursor.description]
        rows = cursor.fetchall()
    except sqlite3.OperationalError:
        print("   Table custom_zones not found or empty")
        return 0
    
    count = 0
    for row in rows:
        data = dict(zip(columns, row))
        CustomZone.objects.create(
            id=data['id'],
            courier_id=data['courier_id'],
            location_name=data['location_name'],
            zone_code=data['zone_code'],
        )
        count += 1
    
    print(f"   Migrated {count} custom zones")
    return count


def migrate_custom_zone_rates(sqlite_conn):
    """Migrate custom_zone_rates table"""
    print("\n[4/6] Migrating Custom Zone Rates...")
    cursor = sqlite_conn.cursor()
    
    try:
        cursor.execute("SELECT * FROM custom_zone_rates")
        columns = [description[0] for description in cursor.description]
        rows = cursor.fetchall()
    except sqlite3.OperationalError:
        print("   Table custom_zone_rates not found or empty")
        return 0
    
    count = 0
    for row in rows:
        data = dict(zip(columns, row))
        CustomZoneRate.objects.create(
            id=data['id'],
            courier_id=data['courier_id'],
            from_zone=data['from_zone'],
            to_zone=data['to_zone'],
            rate_per_kg=float(data.get('rate_per_kg', 0.0)),
        )
        count += 1
    
    print(f"   Migrated {count} custom zone rates")
    return count


def migrate_orders(sqlite_conn):
    """Migrate orders table"""
    print("\n[5/6] Migrating Orders...")
    cursor = sqlite_conn.cursor()
    
    try:
        cursor.execute("SELECT * FROM orders")
        columns = [description[0] for description in cursor.description]
        rows = cursor.fetchall()
    except sqlite3.OperationalError:
        print("   Table orders not found or empty")
        return 0
    
    count = 0
    for row in rows:
        data = dict(zip(columns, row))
        
        # Parse JSON fields
        cost_breakdown = data.get('cost_breakdown')
        if isinstance(cost_breakdown, str):
            try:
                cost_breakdown = json.loads(cost_breakdown)
            except:
                cost_breakdown = None
        
        Order.objects.create(
            id=data['id'],
            order_number=data['order_number'],
            recipient_name=data['recipient_name'],
            recipient_contact=data['recipient_contact'],
            recipient_address=data['recipient_address'],
            recipient_pincode=int(data['recipient_pincode']),
            recipient_city=data.get('recipient_city'),
            recipient_state=data.get('recipient_state'),
            recipient_phone=data.get('recipient_phone'),
            recipient_email=data.get('recipient_email'),
            sender_pincode=int(data['sender_pincode']),
            sender_name=data.get('sender_name'),
            sender_address=data.get('sender_address'),
            sender_phone=data.get('sender_phone'),
            weight=float(data['weight']),
            length=float(data['length']),
            width=float(data['width']),
            height=float(data['height']),
            volumetric_weight=float(data['volumetric_weight']) if data.get('volumetric_weight') else None,
            applicable_weight=float(data['applicable_weight']) if data.get('applicable_weight') else None,
            payment_mode=data.get('payment_mode', 'prepaid'),
            order_value=Decimal(str(data.get('order_value', 0))),
            item_type=data.get('item_type'),
            sku=data.get('sku'),
            quantity=int(data.get('quantity', 1)),
            item_amount=Decimal(str(data.get('item_amount', 0))),
            status=data.get('status', 'draft'),
            selected_carrier=data.get('selected_carrier'),
            total_cost=Decimal(str(data['total_cost'])) if data.get('total_cost') else None,
            cost_breakdown=cost_breakdown,
            awb_number=data.get('awb_number'),
            zone_applied=data.get('zone_applied'),
            mode=data.get('mode'),
            created_at=parse_datetime(data.get('created_at')),
            updated_at=parse_datetime(data.get('updated_at')),
            booked_at=parse_datetime(data.get('booked_at')),
            notes=data.get('notes'),
        )
        count += 1
    
    print(f"   Migrated {count} orders")
    return count


def migrate_ftl_orders(sqlite_conn):
    """Migrate ftl_orders table"""
    print("\n[6/6] Migrating FTL Orders...")
    cursor = sqlite_conn.cursor()
    
    try:
        cursor.execute("SELECT * FROM ftl_orders")
        columns = [description[0] for description in cursor.description]
        rows = cursor.fetchall()
    except sqlite3.OperationalError:
        print("   Table ftl_orders not found or empty")
        return 0
    
    count = 0
    for row in rows:
        data = dict(zip(columns, row))
        
        FTLOrder.objects.create(
            id=data['id'],
            order_number=data['order_number'],
            name=data['name'],
            email=data.get('email'),
            phone=data['phone'],
            source_city=data['source_city'],
            source_address=data.get('source_address', 'Address not provided'),
            source_pincode=int(data['source_pincode']),
            destination_city=data['destination_city'],
            destination_pincode=int(data['destination_pincode']),
            container_type=data['container_type'],
            base_price=Decimal(str(data['base_price'])),
            escalation_amount=Decimal(str(data['escalation_amount'])),
            price_with_escalation=Decimal(str(data['price_with_escalation'])),
            gst_amount=Decimal(str(data['gst_amount'])),
            total_price=Decimal(str(data['total_price'])),
            status=data.get('status', 'draft'),
            created_at=parse_datetime(data.get('created_at')),
            updated_at=parse_datetime(data.get('updated_at')),
            booked_at=parse_datetime(data.get('booked_at')),
            notes=data.get('notes'),
        )
        count += 1
    
    print(f"   Migrated {count} FTL orders")
    return count


def reset_sequences():
    """Reset PostgreSQL sequences to avoid ID conflicts"""
    print("\n[7/7] Resetting PostgreSQL sequences...")
    
    with connection.cursor() as cursor:
        tables = ['couriers', 'city_routes', 'custom_zones', 'custom_zone_rates', 'orders', 'ftl_orders']
        for table in tables:
            try:
                cursor.execute(f"""
                    SELECT setval(pg_get_serial_sequence('{table}', 'id'), 
                           COALESCE((SELECT MAX(id) FROM {table}), 1), true)
                """)
                print(f"   Reset sequence for {table}")
            except Exception as e:
                print(f"   Warning: Could not reset sequence for {table}: {e}")


def main():
    print("=" * 60)
    print("SQLite to PostgreSQL Migration")
    print("=" * 60)
    
    # Check PostgreSQL connection
    print("\nConnecting to PostgreSQL...")
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT version()")
            version = cursor.fetchone()[0]
            print(f"   Connected: {version[:50]}...")
    except Exception as e:
        print(f"ERROR: Could not connect to PostgreSQL: {e}")
        print("\nMake sure PostgreSQL is running:")
        print("   docker-compose -f docker-compose-dev.yml up -d")
        sys.exit(1)
    
    # Run migrations to create tables
    print("\nRunning Django migrations...")
    call_command('migrate', verbosity=0)
    print("   Migrations complete")
    
    # Connect to SQLite
    print("\nConnecting to SQLite database...")
    sqlite_conn = get_sqlite_connection()
    print(f"   Connected to {BASE_DIR / 'logistics.db'}")
    
    # Clear existing data (if any)
    print("\nClearing existing PostgreSQL data...")
    FTLOrder.objects.all().delete()
    Order.objects.all().delete()
    CustomZoneRate.objects.all().delete()
    CustomZone.objects.all().delete()
    CityRoute.objects.all().delete()
    Courier.objects.all().delete()
    print("   Cleared")
    
    # Migrate data
    totals = {}
    totals['couriers'] = migrate_couriers(sqlite_conn)
    totals['city_routes'] = migrate_city_routes(sqlite_conn)
    totals['custom_zones'] = migrate_custom_zones(sqlite_conn)
    totals['custom_zone_rates'] = migrate_custom_zone_rates(sqlite_conn)
    totals['orders'] = migrate_orders(sqlite_conn)
    totals['ftl_orders'] = migrate_ftl_orders(sqlite_conn)
    
    # Reset sequences
    reset_sequences()
    
    # Summary
    print("\n" + "=" * 60)
    print("Migration Complete!")
    print("=" * 60)
    print("\nRecords migrated:")
    for table, count in totals.items():
        print(f"   {table}: {count}")
    
    sqlite_conn.close()
    print("\nDone!")


if __name__ == '__main__':
    main()
