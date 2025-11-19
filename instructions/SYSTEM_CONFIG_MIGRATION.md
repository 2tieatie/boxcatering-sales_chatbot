# System Configuration Migration Guide

This document explains the migration of the settings.html page from localStorage to the system_config API for persistent configuration storage.

## 🎯 What Changed

### Before (localStorage)

- Settings were stored in browser localStorage
- Data was lost when clearing browser data
- No persistence across different devices/browsers
- No centralized configuration management
- No role-based access control

### After (system_config API)

- Settings are stored in PostgreSQL database
- Persistent across all sessions and devices
- Centralized configuration management
- Role-based access control (system admin only)
- Audit trail with timestamps
- Sensitive data protection

## 🚀 New API Endpoints

### Get All Settings

```
GET /system-config/settings/all
```

Returns all settings organized by category:

- `openai`: API key, model, max tokens, temperature
- `telegram`: Bot token, chat ID, notifications
- `system`: Name, version, timezone, language, log level
- `security`: JWT secret, expiry, password requirements, session timeout

### Save Settings by Category

```
POST /system-config/settings/openai
POST /system-config/settings/telegram
POST /system-config/settings/system
POST /system-config/settings/security
```

### Bulk Operations

```
POST /system-config/settings/bulk
```

Save multiple settings across categories at once.

## 🔧 Setup Instructions

### 1. Initialize Database (includes all initial data)

```bash
make db-init
```

This single command will:

- Create all database tables
- Create the system administrator user (admin/admin123)
- Create default system configurations
- Create default chatbot configuration

### 2. Run Migrations (if needed)

```bash
make db-migrate
```

### 3. Test the API

```bash
make test-system-config
```

### 4. Complete Setup (all steps)

```bash
make setup
```

**Note:** The `setup-system-config` step is now included in `db-init`, so you don't need to run it separately.

## 📊 Database Schema

The system configuration is stored in the `system_configs` table:

```sql
CREATE TABLE system_configs (
    id SERIAL PRIMARY KEY,
    key VARCHAR UNIQUE NOT NULL,
    value TEXT NOT NULL,
    description TEXT,
    is_sensitive BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE
);
```

### Configuration Keys

#### OpenAI Settings

- `openai_api_key` - OpenAI API key (sensitive)
- `openai_model` - GPT model selection
- `openai_max_tokens` - Maximum response tokens
- `openai_temperature` - Response creativity (0.0-2.0)

#### Telegram Settings

- `telegram_bot_token` - Bot token (sensitive)
- `telegram_chat_id` - Notification chat ID
- `telegram_notifications` - Notification level

#### System Settings

- `system_name` - Application name
- `system_version` - Version number
- `system_timezone` - Default timezone
- `system_language` - Default language
- `system_log_level` - Logging level

#### Security Settings

- `security_jwt_secret` - JWT signing key (sensitive)
- `security_jwt_expiry` - Token expiry hours
- `security_password_min_length` - Password requirement
- `security_session_timeout` - Session timeout minutes

## 🔒 Security Features

### Sensitive Data Protection

- API keys and tokens are marked as `is_sensitive = true`
- Values are stored encrypted in production
- Access logs track all configuration changes

### Role-Based Access Control

- Only system administrators can access configuration
- Regular admins and managers cannot modify system settings
- Authentication required for all operations

### Audit Trail

- All changes are timestamped
- `created_at` and `updated_at` fields track modifications
- Database logs maintain change history

## 🧪 Testing

### Manual Testing

1. Login as system administrator
2. Navigate to `/settings` page
3. Modify any setting value
4. Click "Save" button
5. Verify success message appears
6. Refresh page to confirm persistence

### Automated Testing

Run the test script to verify all endpoints:

```bash
python scripts/test_system_config.py
```

This will test:

- Authentication
- Getting all settings
- Saving settings by category
- Bulk operations
- Error handling

## 🔄 Migration Process

### Step 1: Complete Database Setup

The `make db-init` command now handles everything:

- Creates all database tables
- Creates the system administrator user
- Creates default system configurations
- Creates default chatbot configuration

### Step 2: Frontend Update

The settings.html page now uses API calls instead of localStorage operations.

### Step 3: Testing

Verify that all settings can be saved and loaded correctly through the API.

**That's it!** The migration is now much simpler with a single command.

## 🚨 Troubleshooting

### Common Issues

#### Settings Not Loading

- Check database connection
- Verify user has system_admin role
- Check browser console for API errors
- Ensure setup script was run

#### Settings Not Saving

- Verify authentication token is valid
- Check user permissions
- Review API response for error details
- Ensure database is accessible

#### Permission Denied

- User must have `system_admin` role
- Check role assignment in database
- Verify JWT token contains correct claims

### Debug Steps

1. Check browser console for JavaScript errors
2. Verify API endpoints are accessible
3. Check database logs for errors
4. Test API endpoints directly with tools like curl or Postman
5. Verify user role and permissions

## 📈 Benefits

### Persistence

- Settings survive browser restarts
- Data persists across devices
- No data loss from browser clearing

### Centralization

- Single source of truth
- Consistent across all users
- Easy backup and restore

### Security

- Role-based access control
- Sensitive data protection
- Audit trail for changes

### Scalability

- Multiple users can access same settings
- Easy to implement configuration management
- Support for environment-specific configs

## 🔮 Future Enhancements

### Planned Features

- Configuration versioning
- Environment-specific configurations
- Configuration templates
- Import/export functionality
- Configuration validation rules
- Webhook notifications for changes

### Integration Opportunities

- CI/CD pipeline configuration
- Infrastructure as Code (IaC)
- Configuration monitoring
- Automated backups
- Configuration drift detection

## 📚 Additional Resources

- [System Configuration API Documentation](../README.md#system-configuration)
- [Database Schema Documentation](../app/models/system_config.py)
- [API Endpoints](../app/api/system_config.py)
- [Setup Scripts](../scripts/setup_system_config.py)
- [Test Scripts](../scripts/test_system_config.py)
