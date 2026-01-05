# Django Admin Access Guide
## How to Access the Admin Panel
### 1. Start the Server

```bash
python manage.py runserver 8000
```

Or use the quick start script:
```bash
# Windows
start_django.bat

# Linux/Mac
./start_django.sh
```

### 2. Access the Admin Panel

Open your browser and go to:
```
http://localhost:8001/django-admin/
```

### 3. Login Credentials

An admin user already exists in your database.

**If you don't know the password**, you can reset it:

```bash
python manage.py changepassword admin
```

### 4. Create a New Admin User (Optional)

If you want to create a different admin user:

**Interactive method:**
```bash
python manage.py createsuperuser
```
Then follow the prompts to enter username, email, and password.

**Or use the script:**
```bash
python create_admin.py
```
This creates a user with:
- Username: `admin`
- Password: `admin123`
- Email: `admin@example.com`

**IMPORTANT:** Change the password after first login!

## Admin Panel Features

Once logged in, you can:

### Order Management
- **View all orders** with advanced filtering
- **Search** by order number, recipient name, contact
- **Filter** by:
  - Status (draft, pending, booked, in_transit, delivered, cancelled)
  - Payment mode (COD, prepaid)
  - Selected carrier
  - Date ranges
- **Edit orders** (update any field)
- **Delete orders** (only DRAFT status)
- **Export data** using admin actions

### What You Can See
- Order number, recipient details, contact info
- Package dimensions and weight calculations
- Shipment details (carrier, cost, zone, mode)
- Timestamps (created, updated, booked)
- Payment information
- Tracking details (AWB number)

### Permissions
- Full read/write access to all orders
- Can only delete DRAFT orders (safety feature)
- All changes are logged

## Alternative: API Admin Endpoints

You can also manage data via API using your `X-Admin-Token` header:

```bash
# Get all carrier rates
curl -H "X-Admin-Token: YOUR_ADMIN_PASSWORD" \
     http://localhost:8001/api/admin/rates

# Add new carrier
curl -X POST \
     -H "X-Admin-Token: YOUR_ADMIN_PASSWORD" \
     -H "Content-Type: application/json" \
     -d '{"carrier_name":"New Carrier",...}' \
     http://localhost:8001/api/admin/rates/add
```

Your `X-Admin-Token` is the `ADMIN_PASSWORD` from your `.env` file.

## Troubleshooting

### Can't login?
1. Make sure the server is running
2. Check you're using the correct URL: `/django-admin/` (not `/admin/`)
3. Reset password: `python manage.py changepassword admin`

### Forgot username?
List all superusers:
```bash
python manage.py shell -c "from django.contrib.auth import get_user_model; User = get_user_model(); print([u.username for u in User.objects.filter(is_superuser=True)])"
```

### Create new admin:
```bash
python create_admin.py
```

---

**Admin Panel URL:** http://localhost:8001/django-admin/
**API Documentation:** http://localhost:8001/docs/
