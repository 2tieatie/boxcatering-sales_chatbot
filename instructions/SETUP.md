# 🚀 Local Setup Guide for Boxcatering Chatbot

This guide will help you set up and run the Boxcatering Chatbot application locally on your machine.

## 📋 Prerequisites

- **Python 3.8+** installed
- **PostgreSQL** database server running
- **Git** (to clone the repository)

## 🗄️ Database Setup

### 1. Install PostgreSQL

**Windows:**

- Download from [PostgreSQL official website](https://www.postgresql.org/download/windows/)
- Install with default settings
- Remember the password you set for the `postgres` user

**macOS:**

```bash
brew install postgresql
brew services start postgresql
```

**Linux (Ubuntu/Debian):**

```bash
sudo apt update
sudo apt install postgresql postgresql-contrib
sudo systemctl start postgresql
sudo systemctl enable postgresql
```

### 2. Create Database

**Option A: Using the provided script**

```bash
# Connect to PostgreSQL as superuser
sudo -u postgres psql

# Run the database creation script
\i scripts/create_db.sql

# Exit PostgreSQL
\q
```

**Option B: Manual creation**

```bash
# Connect to PostgreSQL
sudo -u postgres psql

# Create database
CREATE DATABASE boxcatering_chatbot;

# Exit
\q
```

## 🐍 Python Environment Setup

### 1. Install Dependencies

```bash
# Install required packages
pip install -r requirements.txt

# Or if you prefer using uv (faster)
uv sync
```

### 2. Environment Configuration

```bash
# Copy environment template
cp env.example .env

# Edit .env file with your database credentials
# Update DATABASE_URL with your PostgreSQL connection string
```

## 🚀 Quick Setup (Recommended)

Run the automated setup script:

```bash
python scripts/setup.py
```

This script will:

- ✅ Check Python version
- ✅ Verify dependencies
- ✅ Create/update .env file
- ✅ Test database connection
- ✅ Initialize database tables
- ✅ Create system administrator user

## 🔑 Default Login Credentials

After running the setup script, you can login with:

- **Username:** `admin`
- **Password:** `admin123`
- **Role:** `system_admin`

⚠️ **IMPORTANT:** Change the default password after your first login!

## 🏃‍♂️ Running the Application

### 1. Start the FastAPI server

```bash
python -m app.main
```

### 2. Access the application

Open your browser and go to: `http://localhost:8000`

### 3. Login

Use the credentials above to access the system configuration page and other features.

## 🛠️ Manual Setup Steps

If you prefer to set up manually:

### 1. Initialize Database

```bash
python scripts/init_db.py
```

### 2. Create Admin User

```bash
python scripts/create_admin.py
```

### 3. Start Application

```bash
python -m app.main
```

## 🔧 Troubleshooting

### Database Connection Issues

- Ensure PostgreSQL is running
- Check database credentials in `.env`
- Verify database `boxcatering_chatbot` exists
- Test connection: `psql -h localhost -U postgres -d boxcatering_chatbot`

### Python Package Issues

- Update pip: `pip install --upgrade pip`
- Install packages individually if needed
- Check Python version compatibility

### Port Already in Use

- Change port in `.env` file
- Kill process using port 8000: `lsof -ti:8000 | xargs kill -9`

## 📱 Accessing System Configuration

Once logged in as the system administrator:

1. **Navigate to:** `/system-config` or click "System Config" in navigation
2. **Add configurations** for:
   - OpenAI API keys
   - Telegram bot tokens
   - Other system parameters
3. **Manage existing configurations** with full CRUD operations

## 🔒 Security Notes

- Change default password immediately
- Use strong, unique passwords
- Keep `.env` file secure and never commit it to version control
- Use environment variables in production
- Regularly update dependencies

## 📞 Support

If you encounter issues:

1. Check the troubleshooting section above
2. Review error logs in the terminal
3. Ensure all prerequisites are met
4. Verify database connectivity

---

**Happy coding! 🎉**
