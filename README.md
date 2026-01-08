# LogiRate API - Django Edition 🚚

A high-performance, production-ready logistics engine built with **Django** and **Django REST Framework**. This application automates shipping cost comparisons across multiple carriers by resolving Indian 6-digit pincodes into specific shipping zones (A-E) using a localized Pincode Master database.

## 🌟 Core Features

- **Pincode Intelligence**: Resolves City, State, and District using an optimized CSV master database.
- **Smart Zone Resolution**: Implements a strict priority-based hierarchy:
    - **Zone A (Local)**: Intra-city shipments.
    - **Zone B (Regional)**: Intra-state shipments.
    - **Zone C (Metro)**: Hub-to-Hub shipments between major Tier-1 cities.
    - **Zone D (National)**: Standard cross-state shipments (Rest of India).
    - **Zone E (Special)**: **Highest Priority** override for North East states, J&K, and Ladakh.
- **Dynamic Pricing Engine**: Calculates costs based on:
    - Base weight slabs (e.g., 0.5kg).
    - Additional weight increments.
    - **COD Logic**: "Higher of" fixed fee vs. percentage of order value.
    - **Taxation**: Integrated 18% GST (configurable).

## 🧠 Carrier Logic Models

The engine supports three distinct routing/pricing models:

1.  **Standard Zonal Priority** (Default)
    - Resolves Zones based on hierarchy: Local (A) -> State (B) -> Metro (C) -> National (D) -> Special (E).
    - Used for standard zonal carriers.

2.  **City-to-City Logic** (ACPL)
    - Implements direct point-to-point routing logic.
    - Uses `ACPL_Serviceable_Pincodes.csv` to map specific source-destination pairs (e.g., Bhiwandi <-> Serviceable City).
    - Supports bidirectional routing checks.

3.  **Carrier-Specific Zones** (BlueDart, V-Trans)
    - **BlueDart**: Uses Region-based mapping via `BlueDart_Serviceable Pincodes.csv` to determine unique zones (e.g., Zone 1, Zone 2).
    - **V-Trans**: Implements custom zonal definitions specific to the carrier's network structure.

- **Order Management**: Full CRUD operations for logistics order tracking.
- **Admin Analytics**: Advanced reporting with revenue, profit margins, and carrier performance metrics.

## 🛠️ Tech Stack

- **Backend**: Django 5.2.8 + Django REST Framework 3.16
- **API Documentation**: drf-spectacular (OpenAPI/Swagger)
- **Data Validation**: DRF Serializers (migrated from Pydantic V2)
- **Data Processing**: Pandas (Initial CSV indexing)
- **Frontend**: Tailwind CSS & Vanilla JS (Fetch API)
- **Configuration**: JSON-driven settings for easy updates to GST and Metro lists.
- **Security**: Custom X-Admin-Token authentication, CORS headers, strong password validation

## 📁 Project Structure

```text
Courier_Module/
├── config/                      # Django project settings
│   ├── settings.py              # Main configuration
│   ├── urls.py                  # Root URL routing
│   ├── wsgi.py                  # WSGI application
│   └── asgi.py                  # ASGI application
├── courier/                     # Main Django app
│   ├── models.py                # Django ORM models
│   ├── serializers.py           # DRF serializers
│   ├── views/                   # API ViewSets
│   │   ├── admin.py             # Admin endpoints
│   │   ├── orders.py            # Order management
│   │   ├── public.py            # Public facing APIs
│   │   └── ...
│   ├── urls.py                  # App URL routing
│   ├── permissions.py           # Custom permissions
│   ├── authentication.py        # Admin token auth
│   ├── admin.py                 # Django admin configuration
│   ├── engine.py                # Calculation logic (GST, COD, Slabs)
│   ├── zones.py                 # Pincode & Zone Resolution Logic
│   ├── config/                  # JSON Configuration Files

│   │   ├── metro_cities.json
│   │   └── special_states.json
│   └── data/                    # Reference Data
│       ├── pincode_master.csv
│       └── rate_cards.json      # Carrier Rates Database
├── static/                      # Static files (dashboard, CSS, JS)
├── manage.py                    # Django management script
├── requirements_django.txt      # Python dependencies
├── logistics.db                 # SQLite database
└── .env                         # Environment variables
```

## 🚀 Getting Started

### 1. Install Dependencies

```bash
pip install -r requirements_django.txt
```

### 2. Configure Environment Variables

Create or update `.env` file:

```env
# REQUIRED: Strong admin password (12+ chars, mixed complexity)
ADMIN_PASSWORD=YourSecurePassword123!

# Optional Django settings
DJANGO_SECRET_KEY=your-secret-key-here
DEBUG=True
ALLOWED_HOSTS=*
```

### 3. Run Database Migrations

```bash
python manage.py migrate
```

### 4. Create Django Superuser (Optional)

```bash
python manage.py createsuperuser
```

### 5. Run the Development Server

```bash
python manage.py runserver 8001
```

### 6. Access the Application

- **Dashboard**: http://localhost:8001/static/dashboard.html
- **API Documentation (Swagger)**: http://localhost:8001/docs/
- **API Documentation (ReDoc)**: http://localhost:8001/redoc/
- **Django Admin**: http://localhost:8001/django-admin/
- **Health Check**: http://localhost:8001/api/health

## 📊 API Endpoints

### Public Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Health check |
| POST | `/api/compare-rates` | Compare carrier rates |
| GET | `/api/pincode/{pincode}/` | Lookup pincode details |
| POST | `/api/orders/` | Create new order |
| GET | `/api/orders/` | List all orders |
| GET | `/api/orders/{id}/` | Get order details |
| PUT | `/api/orders/{id}/` | Update order |
| DELETE | `/api/orders/{id}/` | Delete order (draft only) |
| POST | `/api/orders/compare-carriers/` | Compare rates for orders |
| POST | `/api/orders/book-carrier/` | Book carrier for orders |

### Admin Endpoints (Requires X-Admin-Token Header)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/admin/rates` | Get all carrier rates |
| POST | `/api/admin/rates/update` | Update carrier rates |
| POST | `/api/admin/rates/add` | Add new carrier |

## 📝 API Usage Example

### Request: POST `/api/compare-rates`

```json
{
  "source_pincode": 400001,
  "dest_pincode": 110001,
  "weight": 0.8,
  "is_cod": true,
  "order_value": 1500,
  "mode": "Both"
}
```

### Response

```json
[
  {
    "carrier": "Ekart Surface",
    "total_cost": 108.75,
    "breakdown": {
      "base_forward": 29.96,
      "additional_weight": 18.19,
      "cod": 31.99,
      "escalation": 12.02,
      "gst": 16.59,
      "applied_gst_rate": "18%",
      "applied_escalation_rate": "15%"
    },
    "applied_zone": "Zone A (Metropolitan)",
    "mode": "Surface"
  }
]
```

## 🔒 Security Features

1. **Strong Password Validation**: Enforces 12+ character passwords with complexity requirements
2. **Admin Token Authentication**: Custom `X-Admin-Token` header for admin endpoints
3. **CORS Protection**: Configurable CORS headers
4. **Rate Limiting**: 30 requests/minute on public endpoints
5. **SQL Injection Protection**: Django ORM parameterized queries
6. **Input Validation**: Comprehensive DRF serializer validation

## ⚙️ Configuration

### Update Carrier Rates

Edit `courier/data/rate_cards.json` or use the admin API endpoint.

### Update Metro Cities

Edit `courier/config/metro_cities.json` without touching core Python logic.

### Update System Settings

### Update System Settings

Edit `config/settings.py` (look for `COURIER_BUSINESS_RULES`) to change:
- GST Rate
- Escalation Rate (Profit Margin)
- Default Weight Slab

## 🏗️ Production Deployment

### Using Gunicorn

```bash
gunicorn config.wsgi:application --bind 0.0.0.0:8001 --workers 4
```

### Using Docker (Example)

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements_django.txt .
RUN pip install -r requirements_django.txt
COPY . .
RUN python manage.py collectstatic --noinput
CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8001"]
```

### Environment Variables for Production

```env
DEBUG=False
ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com
DJANGO_SECRET_KEY=your-very-secret-key-here
ADMIN_PASSWORD=YourProductionPassword123!
```

## 🧪 Testing

```bash
# Run tests
pytest

# Run with coverage
pytest --cov=courier

# Run Django tests
python manage.py test courier
```

## 📚 Django Admin Interface

Access the powerful Django admin at `/django-admin/` to:
- Manage orders with advanced filtering
- Search by order number, recipient, contact
- View order status and shipment details
- Filter by carrier, status, date ranges
- Only delete DRAFT orders (safety feature)

## 🔄 Migration from FastAPI

This project was successfully migrated from FastAPI to Django while maintaining:
- ✅ All business logic (engine.py, zones.py)
- ✅ Existing database compatibility
- ✅ API endpoint structure
- ✅ Admin authentication system
- ✅ Static dashboard files
- ✅ Configuration files

## 🤝 Integration with Existing Systems

This Django implementation is designed to integrate seamlessly with existing Django-based systems:

- **Shared User Authentication**: Can use Django's built-in auth system
- **Unified Admin Interface**: Integrates into existing Django admin
- **Database Integration**: Can share database with other Django apps
- **Middleware Compatibility**: Works with existing Django middleware
- **ORM Benefits**: Use Django QuerySets for complex queries across apps

## 📞 Support

For issues or questions, please check:
- API Documentation at `/docs/`
- Django Admin interface for data management
- Application logs at `app.log`


