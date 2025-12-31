from sqlalchemy import create_engine, Column, Integer, String, Float, Boolean, DateTime, JSON, Enum as SQLEnum
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import enum
import os

# Database setup
DATABASE_URL = "sqlite:///./logistics.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Enums
class OrderStatus(str, enum.Enum):
    DRAFT = "draft"
    PENDING = "pending"
    BOOKED = "booked"
    IN_TRANSIT = "in_transit"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"

class PaymentMode(str, enum.Enum):
    COD = "cod"
    PREPAID = "prepaid"

# Models
class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True)
    order_number = Column(String, unique=True, index=True, nullable=False)

    # Recipient Details
    recipient_name = Column(String, nullable=False)
    recipient_contact = Column(String, nullable=False)  # Mandatory contact number
    recipient_address = Column(String, nullable=False)
    recipient_pincode = Column(Integer, nullable=False)
    recipient_city = Column(String)  # Auto-filled from pincode
    recipient_state = Column(String)  # Auto-filled from pincode
    recipient_phone = Column(String)  # Additional phone if needed
    recipient_email = Column(String)

    # Sender Details (optional, can be defaulted)
    sender_pincode = Column(Integer, nullable=False)
    sender_name = Column(String)
    sender_address = Column(String)
    sender_phone = Column(String)

    # Box Details
    weight = Column(Float, nullable=False)  # in kg (actual weight)
    length = Column(Float, nullable=False)  # in cm (mandatory)
    width = Column(Float, nullable=False)   # in cm (mandatory)
    height = Column(Float, nullable=False)  # in cm (mandatory)
    volumetric_weight = Column(Float)  # calculated: (L x W x H) / 5000
    applicable_weight = Column(Float)  # max(actual_weight, volumetric_weight)

    # Payment
    payment_mode = Column(SQLEnum(PaymentMode), nullable=False, default=PaymentMode.PREPAID)
    order_value = Column(Float, default=0.0)  # for COD

    # Items Info
    item_type = Column(String)  # e.g., Electronics, Clothing, Documents
    sku = Column(String)
    quantity = Column(Integer, default=1)
    item_amount = Column(Float, default=0.0)

    # Order Status & Tracking
    status = Column(SQLEnum(OrderStatus), default=OrderStatus.DRAFT)

    # Shipment Details (filled after carrier selection)
    selected_carrier = Column(String)
    total_cost = Column(Float)
    cost_breakdown = Column(JSON)  # stores the full breakdown
    awb_number = Column(String)  # Air Waybill number from carrier
    zone_applied = Column(String)
    mode = Column(String)  # Surface/Air

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    booked_at = Column(DateTime)

    # Additional metadata
    notes = Column(String)

# Database helper functions
def get_db():
    """Dependency for FastAPI routes"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    """Initialize database tables"""
    Base.metadata.create_all(bind=engine)
    print("Database initialized successfully")

if __name__ == "__main__":
    init_db()
