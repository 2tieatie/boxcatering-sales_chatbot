# Boxcatering Chatbot

AI-powered chatbot for boxcatering business with intelligent manager handover capabilities.

## Features

- **AI-Powered Chatbot**: Built with OpenAI GPT models for intelligent customer interactions
- **Manager Handover**: Automatic escalation to human managers when needed
- **Telegram Notifications**: Real-time alerts for handover requests
- **Role-Based Access Control**: System Admin, Admin, and Manager roles
- **Comprehensive Logging**: Full conversation and order history tracking
- **WebSocket Support**: Real-time chat communication
- **PostgreSQL Database**: Robust data storage with SQLAlchemy ORM

## Architecture

The system follows a clean architecture pattern with:

- **FastAPI Backend**: Modern, fast web framework
- **WebSocket Chat**: Real-time communication
- **AI Service Integration**: OpenAI GPT for intelligent responses
- **Database Models**: Comprehensive data structure
- **Role-Based Security**: JWT-based authentication
- **Telegram Integration**: Manager notifications

## Database Schema

### Core Tables

- **Users**: System users with role-based permissions
- **Conversations**: Chat sessions with handover states
- **Messages**: Individual chat messages
- **Customers**: Client information
- **Orders**: Customer orders (similar to Odoo sale.order)
- **ChatbotConfig**: Bot configuration and prompts
- **SystemConfig**: System parameters and settings

### Handover States

- `NONE`: Normal bot conversation
- `HANDOVER_PENDING`: Handover requested, notification sent
- `HANDOVER_IN_PROGRESS`: Manager assigned to case
- `RESOLVED_BY_MANAGER`: Case closed by manager

## Installation

### Prerequisites

- Python 3.12+
- PostgreSQL 12+
- OpenAI API key
- Telegram bot token (optional)

### Setup

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd boxcatering-chatbot
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -e .
   ```

4. **Environment configuration**
   ```bash
   cp env.example .env
   # Edit .env with your configuration
   ```

5. **Database setup**
   ```bash
   # Create PostgreSQL database
   createdb boxcatering_chatbot
   
   # Run migrations
   alembic upgrade head
   ```

6. **Run the application**
   ```bash
   python -m app.main
   ```

## Configuration

### Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `DATABASE_URL` | PostgreSQL connection string | Yes |
| `OPENAI_API_KEY` | OpenAI API key | Yes |
| `OPENAI_MODEL` | GPT model to use | No (default: gpt-4) |
| `TELEGRAM_BOT_TOKEN` | Telegram bot token | No |
| `TELEGRAM_CHAT_ID` | Telegram chat ID for notifications | No |
| `SECRET_KEY` | JWT secret key | Yes |
| `DEBUG` | Debug mode | No (default: false) |

### Database Configuration

The system uses PostgreSQL with the following connection format:
```
postgresql://username:password@host:port/database_name
```

## API Endpoints

### Chat
- `GET /chat/ws` - WebSocket endpoint for real-time chat

### Health
- `GET /health` - Health check endpoint

### Authentication (to be implemented)
- `POST /auth/login` - User login
- `POST /auth/register` - User registration

### Users (to be implemented)
- `GET /users/` - List users
- `POST /users/` - Create user
- `PUT /users/{id}` - Update user
- `DELETE /users/{id}` - Delete user

### Conversations (to be implemented)
- `GET /conversations/` - List conversations
- `GET /conversations/{id}` - Get conversation details
- `PUT /conversations/{id}` - Update conversation

### Orders (to be implemented)
- `GET /orders/` - List orders
- `GET /orders/{id}` - Get order details
- `PUT /orders/{id}` - Update order

## Usage

### WebSocket Chat

Connect to the WebSocket endpoint and send messages in this format:

```json
{
  "session_id": "unique_session_id",
  "sender": "user",
  "message": "Hello, I need information about your catering services",
  "timestamp": "2025-01-15T10:30:00Z"
}
```

The bot will respond with:

```json
{
  "response": "Hello! I'd be happy to help you with information about our catering services...",
  "handover_to_manager": false,
  "handover_reason": null,
  "handover_reason_description": null
}
```

### Manager Handover

When the AI determines a handover is needed:

```json
{
  "response": "I understand your concern, but I think it would be best to have a manager assist you with this.",
  "handover_to_manager": true,
  "handover_reason": "SENSITIVE_CASE",
  "handover_reason_description": "Customer has a complex complaint that requires human intervention"
}
```

## Development

### Code Quality

The project uses several tools for code quality:

- **Black**: Code formatting
- **isort**: Import sorting
- **flake8**: Linting
- **mypy**: Type checking

### Running Tests

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Format code
black .
isort .

# Lint code
flake8
mypy .
```

### Database Migrations

```bash
# Create new migration
alembic revision --autogenerate -m "Description of changes"

# Apply migrations
alembic upgrade head

# Rollback migration
alembic downgrade -1
```

## Deployment

### Production Considerations

1. **Environment Variables**: Use proper secrets management
2. **Database**: Use connection pooling and proper indexing
3. **Security**: Configure CORS properly, use HTTPS
4. **Monitoring**: Add logging and health checks
5. **Scaling**: Consider using multiple workers

### Docker (to be implemented)

```dockerfile
FROM python:3.12-slim

WORKDIR /app
COPY . .

RUN pip install -e .

EXPOSE 8000

CMD ["python", "-m", "app.main"]
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Ensure code quality checks pass
6. Submit a pull request

## License

[Add your license here]

## Support

For support and questions, please contact [your contact information].
