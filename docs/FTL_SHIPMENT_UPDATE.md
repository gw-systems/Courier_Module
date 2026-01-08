# FTL Shipment Section Update

## Change Summary
Updated the FTL shipment section to show only draft orders and provide only the booking action.

## Changes Made

### JavaScript - `static/js/dashboard/ftl.js`

**`loadShipmentFTLOrders()` function**:
- Changed API call to filter only draft orders: `?status=draft`
- Updated empty state message to "No draft FTL orders"
- Added fallback for null source_address: `${order.source_address || 'Not provided'}`

**`handleShipmentFTLOrderSelection()` function**:
- Removed Edit button logic
- Removed Delete button logic  
- Simplified to only show Book button (since all orders are draft)

### HTML - `templates/dashboard.html`

**Shipment FTL Actions** (lines 336-345):
- Removed Edit button
- Removed Delete button
- Kept only Book button

## Result
The shipment section now:
- Shows ONLY draft FTL orders
- Provides ONLY the "Book" action button
- Cleaner, more focused interface for booking workflow
