# Security Guide

## Admin Password Requirements

The LogiRate API enforces strong password requirements for admin panel access to protect against unauthorized access.

### Password Rules

Your admin password MUST meet ALL of the following requirements:

1. **Minimum Length**: At least 12 characters
2. **Complexity**: Must contain a mix of:
   - Letters (uppercase and/or lowercase)
   - Numbers (0-9)
   - Symbols (e.g., !, @, #, $, %, &, *)
3. **No Common Passwords**: Cannot be:
   - `Transportwale` (default)
   - `admin`
   - `password`
   - `12345678`
   - `admin123`
   - Any other well-known weak password
4. **Not Letters-Only**: Cannot be only alphabetic characters
5. **Not Numbers-Only**: Cannot be only numeric characters

### Valid Password Examples

✅ **Good passwords:**
- `MySecure#Pass2024!`
- `LogiRate@Admin#99`
- `Tr@nsp0rt!Secure#2024`
- `Admin$ecure2024!Pass`

❌ **Bad passwords:**
- `password123` (too common, no symbols)
- `Transportwale` (default password)
- `MySecurePassword` (no numbers or symbols)
- `123456789012` (numbers only)
- `Short#1` (too short, < 12 chars)

### Setting Your Password

1. **Copy the example environment file:**
   ```bash
   cp .env.example .env
   ```

2. **Edit the `.env` file:**
   ```bash
   # Open in your text editor
   nano .env
   ```

3. **Set a strong password:**
   ```env
   ADMIN_PASSWORD=MySecure#Pass2024!
   ```

4. **Save and restart the application**

### What Happens with Weak Passwords?

If your password doesn't meet the requirements, the application will **fail to start** with a clear error message:

```
RuntimeError: CRITICAL: ADMIN_PASSWORD is too weak.
Password must be at least 12 characters long.
```

This is intentional security design - it's better for the app to refuse to start than to allow weak passwords that could be compromised.

### Password Storage

- Passwords are stored in the `.env` file (which is gitignored)
- The `.env` file should **never** be committed to version control
- In production, use environment variables or secrets management
- The password is validated at startup, not stored in code

### Changing Your Password

1. Edit the `.env` file
2. Update the `ADMIN_PASSWORD` value
3. Restart the FastAPI application
4. Use the new password to access the admin panel

### Production Recommendations

For production deployments:

1. **Use a password manager** to generate strong passwords
2. **Rotate passwords regularly** (e.g., every 90 days)
3. **Store in secrets manager** (AWS Secrets Manager, Azure Key Vault, etc.)
4. **Enable HTTPS** for all admin panel access
5. **Monitor login attempts** via application logs
6. **Consider multi-factor authentication** for additional security

### Additional Security Measures

Beyond strong passwords, the application includes:

- **Rate Limiting**: 30 requests/minute on public endpoints
- **Token-based auth**: Admin token sent via X-Admin-Token header
- **Request logging**: All admin actions logged with timestamps
- **Input validation**: Pydantic schemas validate all API inputs
- **Backup mechanism**: Automatic backups before rate card changes

---

## Reporting Security Issues

If you discover a security vulnerability, please report it to:
- **Email**: security@yourcompany.com
- **Do not** create public GitHub issues for security vulnerabilities
- Include steps to reproduce and potential impact

We will respond within 48 hours and work with you to address the issue.
