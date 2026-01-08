# Deprecated Fix Scripts Archive

**Date Archived**: 2026-01-07  
**Reason**: Replaced by Django migration `0021_fix_carrier_configurations.py`

## What Are These Scripts?

These are standalone Python scripts that were previously used to manually patch carrier configurations in the database. They have been **consolidated into a single Django data migration** for better maintainability and deployment consistency.

## Archived Scripts

| Script | Purpose | Replaced By |
|--------|---------|-------------|
| `fix_bluedart.py` | Set BlueDart CSV configuration | Migration 0021: `fix_bluedart_config()` |
| `fix_pricing_logic.py` | Fix ACPL and V-Trans logic | Migration 0021: `fix_acpl_config()` + `fix_vtrans_config()` |
| `update_acpl.py` | Update ACPL fee structures | Migration 0021: `fix_acpl_config()` |
| `update_vtrans.py` | Update V-Trans fee structures | Migration 0021: `fix_vtrans_config()` |
| `test_pricing_fix.py` | Test pricing fixes | Superseded by proper pytest tests |
| `verify_pricing.py` | Verify pricing configs | Superseded by `quick_verify.py` |

## Why Were They Deprecated?

### Problems with Standalone Scripts:
- ❌ **No state tracking**: Could be run multiple times causing corruption
- ❌ **Manual execution**: Required remembering to run on each environment
- ❌ **No rollback**: Breaking changes couldn't be undone
- ❌ **Environment divergence**: No guarantee all environments had same fixes
- ❌ **Not in CI/CD**: Manual step outside automation pipeline

### Benefits of Django Migration:
- ✅ **Automatic execution**: Runs with `python manage.py migrate`
- ✅ **State tracking**: Django tracks applied migrations in database
- ✅ **Rollback support**: Can revert with `migrate courier 0020`
- ✅ **Environment consistency**: All environments get same transformations
- ✅ **Version controlled**: Goes through git, code review, CI/CD

## Current Solution

**Migration**: `courier/migrations/0021_fix_carrier_configurations.py`

This single migration handles all the configuration fixes that these scripts did, with added benefits:
- Properly tracked in `django_migrations` table
- Reversible operations for rollback
- Idempotent (safe to run multiple times)
- Integrated with deployment process

## For Historical Reference

These scripts are kept for:
1. Understanding what configuration changes were made and when
2. Reference if similar fixes are needed in the future
3. Audit trail of manual interventions before migration system

## Do NOT Use These Scripts

⚠️ **WARNING**: Do not run these scripts on current databases. They are kept only for historical reference. Use the migration instead:

```bash
# Correct way (use migration):
python manage.py migrate courier 0021

# Wrong way (don't use these):
# python fix_bluedart.py  ← DEPRECATED
# python update_acpl.py   ← DEPRECATED
```

## See Also

- Migration 0021: `courier/migrations/0021_fix_carrier_configurations.py`
- Migration Guide: Documentation in `.gemini/antigravity/brain/.../MIGRATION_0021_GUIDE.md`
- Verification: `quick_verify.py` in project root

---

**If you need to make similar changes in the future, create a new Django data migration instead of a standalone script.**
