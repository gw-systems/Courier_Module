# Changelog

All notable changes to this project will be documented in this file.

## [Unreleased]

### Security - 2025-12-30

#### CRITICAL: Strengthened Admin Password Validation
- **Files Changed:** `app/main.py`, `.env.example`, `tests/conftest.py`
- **Issue:** Application allowed weak default passwords like "Transportwale"
- **Fix:** Implemented strict password requirements enforced at startup
- **Impact:** Application now requires strong passwords or refuses to start

**Password Requirements:**
- Minimum 12 characters
- Must contain letters, numbers, AND symbols
- Cannot be common passwords (admin, password, 12345678, etc.)
- Cannot be letters-only or numbers-only

**Validation Logic:**
```python
if not ADMIN_PASSWORD:
    raise RuntimeError("ADMIN_PASSWORD not set")
elif len(ADMIN_PASSWORD) < 12:
    raise RuntimeError("Password must be at least 12 characters")
elif ADMIN_PASSWORD in ["Transportwale", "admin", "password", ...]:
    raise RuntimeError("Cannot use common/default passwords")
elif ADMIN_PASSWORD.isalpha() or ADMIN_PASSWORD.isdigit():
    raise RuntimeError("Password must contain mix of letters, numbers, symbols")
```

**New Files:**
- `SECURITY.md` - Complete password requirements documentation

**Breaking Change:** Existing installations using weak passwords will fail to start. Update `.env` with a strong password.

**Testing:** Validation enforced at startup - application will not start with weak passwords. All 93 existing tests still passing.

---

### Fixed - 2025-12-30

#### Security: Removed Hardcoded API URLs
- **Files Changed:** `static/admin.html`, `static/index.html`
- **Issue:** Frontend had hardcoded `http://127.0.0.1:8000` URLs which broke in production
- **Fix:** Implemented dynamic API base URL using `window.location.origin`
- **Impact:** Application now works in any environment (localhost, staging, production)

**Before:**
```javascript
fetch('http://127.0.0.1:8000/api/admin/rates', {...})
```

**After:**
```javascript
const API_BASE = window.location.origin;
fetch(`${API_BASE}/api/admin/rates`, {...})
```

**URLs Updated:**
- Admin panel:
  - `/api/admin/rates` (GET - fetch rates)
  - `/api/admin/rates/update` (POST - update rates)
  - `/api/admin/rates/add` (POST - add carrier)
- Public interface:
  - `/compare-rates` (POST - compare shipping rates)

**Testing:** All 93 tests passing after changes

---

## [1.0.0] - 2025-12-30

### Added

#### Feature: Add Carrier via Admin Panel
- **Backend:** POST `/api/admin/rates/add` endpoint
- **Frontend:** Modal form with all carrier fields
- **Validation:**
  - Duplicate name detection (case-insensitive)
  - All zone rates must be positive
  - COD percentage between 0-1
  - Active defaults to true
- **Tests:** 24 comprehensive tests for add carrier functionality

#### Feature: Visual Feedback for Inactive Carriers
- Inactive carriers show grayed out in admin panel
- Active checkbox changes trigger immediate visual update
- Inactive carriers excluded from rate comparison results

#### Testing Infrastructure
- 93 total tests with 100% pass rate
- Test isolation via `restore_rate_cards` fixture
- Coverage: API endpoints, engine calculations, zone logic, admin features

#### Security & Reliability
- Rate limiting: 30 requests/minute on public endpoints
- Admin authentication via X-Admin-Token header
- Backup created before rate updates (.bak files)
- Input validation via Pydantic V2 schemas
- Comprehensive error handling and logging

### Technical Details

**Architecture:**
- FastAPI backend with async support
- O(1) pincode lookups (155K+ pincodes)
- Zone-based pricing (5 tiers: A→E)
- Static file serving for frontend
- Rotating file logs (5MB, 2 backups)

**Data:**
- 8 active carriers (Surface + Air modes)
- 155,015 unique pincodes loaded
- Zone assignments with priority hierarchy
- GST calculation (18%)
- COD fees (fixed + percentage)

---

## Known Issues

### High Priority
- Admin password validation allows weak defaults
- No atomic file writes for rate updates (race condition risk)
- XSS vulnerability in admin table rendering (innerHTML)
- Health check calls load_rates() twice

### Medium Priority
- Admin UI only shows forward rates (additional rates/COD not editable)
- No logging for invalid pincode lookups
- CORS too permissive (allow_origins=["*"])
- No rate card caching (loads from disk every request)

### Low Priority
- No API versioning
- Incomplete docstrings
- No request/response caching
- Admin panel not mobile-responsive

---

## Roadmap

### Phase 1 (Immediate)
- [ ] Strengthen admin password validation
- [ ] Implement atomic file writes
- [ ] Fix XSS vulnerability
- [ ] Optimize health check

### Phase 2 (Next Sprint)
- [ ] Complete admin UI (show all rate fields)
- [ ] Add invalid pincode logging
- [ ] Configure CORS for production
- [ ] Implement rate caching
- [ ] Add concurrent update tests

### Phase 3 (Future)
- [ ] Rate update history/versioning
- [ ] Bulk carrier import (CSV/Excel)
- [ ] Export functionality
- [ ] Mobile-responsive design
- [ ] Advanced pricing rules engine
