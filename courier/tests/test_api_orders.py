from rest_framework.test import APITestCase
from rest_framework import status
from django.urls import reverse
from courier.models import Order, OrderStatus, Courier, SystemConfig

class OrderAPITest(APITestCase):
    def setUp(self):
        # Create System Config
        SystemConfig.objects.create(
            diesel_price_current=95.0,
            base_diesel_price=90.0
        )
        
        # Create a Courier
        self.courier = Courier.objects.create(
            name="Test Carrier",
            carrier_type="Courier",
            carrier_mode="Surface",
            rate_logic="Zonal_Standard",
            fwd_z_a=50.0,
            add_z_a=10.0,
            is_active=True
        )
        
        # Create an Order
        self.order = Order.objects.create(
            order_number="ORD-TEST-001",
            recipient_name="John Doe",
            recipient_contact="9876543210",
            recipient_address="123 Test St",
            recipient_pincode=411001,
            sender_pincode=110001,
            weight=1.5,
            length=10, width=10, height=10,
            status=OrderStatus.DRAFT
        )

    def test_create_order(self):
        url = reverse('courier:order-list')
        data = {
            "recipient_name": "Jane Doe",
            "recipient_contact": "9876543210",
            "recipient_address": "456 Test St",
            "recipient_pincode": 411001,
            "sender_pincode": 110001,
            "weight": 2.0,
            "length": 10, "width": 10, "height": 10
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Order.objects.count(), 2)

    def test_compare_cards(self):
        # This endpoint is a custom action on viewset
        url = reverse('courier:order-compare-carriers')
        data = {
            "order_ids": [self.order.id]
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Check if our Test Carrier is in results
        carriers = [c['carrier'] for c in response.data['carriers']]
        self.assertIn("Test Carrier", carriers)

    def test_book_carrier(self):
        url = reverse('courier:order-book-carrier')
        data = {
            "order_ids": [self.order.id],
            "carrier_name": "Test Carrier",
            "mode": "Surface"
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, OrderStatus.BOOKED)
        self.assertEqual(self.order.carrier, self.courier)

    def test_book_invalid_carrier(self):
        url = reverse('courier:order-book-carrier')
        data = {
            "order_ids": [self.order.id],
            "carrier_name": "Invalid Carrier",
            "mode": "Surface"
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
