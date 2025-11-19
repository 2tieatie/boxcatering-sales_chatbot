# Access Rights Implementation Summary

This document summarizes the implementation of role-based access control (RBAC) in the Boxcatering Chatbot system according to the requirements specified in `boxcatering-chatbot-requirements.md`.

## Role Hierarchy

The system implements three distinct user roles with a clear hierarchy:

### 1. System Administrator (`system_admin`)

- **Level**: 3 (Highest)
- **Access**: Full system access
- **Capabilities**:
  - Full CRUD access to system configuration parameters
  - Full CRUD access to chatbot configurations
  - Full CRUD access to user management
  - All admin and manager capabilities
  - Can manage users with any role

### 2. Administrator (`admin`)

- **Level**: 2 (Middle)
- **Access**: Administrative access with restrictions
- **Capabilities**:
  - User management (create, read, update, delete)
  - Chatbot configuration management
  - Cannot manage system administrators
  - Cannot create system administrators
  - All manager capabilities

### 3. Manager (`manager`)

- **Level**: 1 (Lowest)
- **Access**: Operational access
- **Capabilities**:
  - View conversation histories (read-only)
  - View customer orders (read-only)
  - Mark orders as processed
  - Take conversations for handover
  - Resolve conversations assigned to them
  - Cannot manage other users
  - Cannot modify system configurations

## API Endpoint Access Control

### System Configuration (`/system-config/*`)

- **Access**: System administrators only
- **Operations**: Full CRUD operations
- **Purpose**: Management of system parameters and sensitive configuration

### Chatbot Configuration (`/chatbot-config/*`)

- **Access**: Administrators and system administrators
- **Operations**: Full CRUD operations
- **Special Endpoints**:
  - `/chatbot-config/active` - All authenticated users can view active configuration

### User Management (`/users/*`)

- **Access Control**:
  - **List users**: Administrators and system administrators only
  - **View user**: Self, or administrators/system administrators
  - **Create user**: Administrators and system administrators
  - **Update user**: Self, or administrators/system administrators
  - **Delete user**: Administrators and system administrators (cannot delete self)

### Conversations (`/conversations/*`)

- **Access Control**:
  - **View conversations**: All authenticated users
  - **Update conversations**: Role-based restrictions
    - Managers: Limited to handover state and self-assignment
    - Administrators: Full update access
  - **Take conversation**: Managers only
  - **Resolve conversation**: Managers only (assigned conversations)

### Orders (`/orders/*`)

- **Access Control**:
  - **View orders**: All authenticated users
  - **Update orders**: Role-based restrictions
    - Managers: Can only mark as processed
    - Administrators: Full update access
  - **Mark processed**: Managers only

### Chat (`/chat/ws`)

- **Access**: WebSocket endpoint (no role restrictions)
- **Purpose**: Customer interaction with chatbot

## Role Hierarchy Enforcement

### User Creation Restrictions

- **System administrators** can create users with any role
- **Administrators** can create managers and other administrators, but not system administrators
- **Managers** cannot create users

### User Management Restrictions

- **System administrators** can manage any user
- **Administrators** can manage managers and other administrators, but not system administrators
- **Managers** cannot manage other users

### Role Promotion Restrictions

- **Administrators** cannot promote users to system administrator role
- **Administrators** cannot modify system administrator accounts
- **System administrators** have no restrictions

## Implementation Details

### Role Service (`app/services/role_service.py`)

Centralized service providing:

- Role validation methods
- Permission checking utilities
- Role hierarchy management
- Access control helper functions

### API Dependencies

Each protected endpoint uses appropriate role dependencies:

- `require_system_admin()` - System administrator only
- `require_admin_or_system_admin()` - Administrator or system administrator
- `require_manager_or_higher()` - Manager, administrator, or system administrator

### Security Features

- JWT-based authentication
- Role-based endpoint protection
- Hierarchical permission enforcement
- Self-modification restrictions
- Cross-role operation prevention

## Compliance with Requirements

✅ **System Administrator Requirements**:

- Full CRUD access to system configuration parameters
- Full administrative rights

✅ **Administrator Requirements**:

- User management and role assignment
- Chatbot configuration management
- Manager-level capabilities

✅ **Manager Requirements**:

- Chatbot testing access
- Conversation history viewing (read-only)
- Order viewing and processing status updates

## Security Considerations

1. **Role Escalation Prevention**: Users cannot promote themselves to higher roles
2. **Self-Deletion Prevention**: Users cannot delete their own accounts
3. **Hierarchical Access Control**: Lower roles cannot manage higher roles
4. **Audit Trail**: All operations are logged through the authentication system
5. **Session Management**: JWT tokens with configurable expiration

## Testing Recommendations

1. **Role Access Testing**: Verify each role can only access permitted endpoints
2. **Permission Boundary Testing**: Test role hierarchy enforcement
3. **Cross-Role Operation Testing**: Ensure lower roles cannot perform higher-role operations
4. **Self-Modification Testing**: Verify users can modify their own profiles appropriately
5. **API Endpoint Testing**: Test all protected endpoints with various user roles

## Future Enhancements

1. **Permission Granularity**: Implement field-level permissions
2. **Audit Logging**: Enhanced operation logging and monitoring
3. **Dynamic Role Assignment**: Runtime role modification capabilities
4. **Permission Templates**: Predefined permission sets for common roles
5. **Access Request Workflow**: Approval-based permission escalation
