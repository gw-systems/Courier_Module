# Template File Location

**IMPORTANT**: The dashboard HTML template is located at:
- `templates/dashboard.html` ← **This is the ONLY file to edit**

**DO NOT** create or edit `static/dashboard.html` - it will cause confusion and caching issues.

## Why This Matters
- Django serves templates from the `templates/` directory
- The `static/` directory is for CSS, JS, and images only
- Having duplicate HTML files causes confusion about which file is being served
- Browser caching can make it appear that changes aren't working

## If Changes Don't Appear
1. Hard refresh the browser (Ctrl+Shift+R)
2. Clear browser cache
3. Restart the Django development server
4. Check that you edited `templates/dashboard.html` (not `static/dashboard.html`)
