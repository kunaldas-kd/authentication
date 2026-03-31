# Authentication Service

A Django-based authentication service for the Common App APIs ecosystem. This service provides secure user authentication, session management, and authorization across the application platform.

## Table of Contents

1. [Overview](#overview)
2. [Project Structure](#project-structure)
3. [Features](#features)
4. [Getting Started](#getting-started)
5. [Configuration](#configuration)
6. [API Endpoints](#api-endpoints)
7. [Security Considerations](#security-considerations)
8. [Troubleshooting](#troubleshooting)

## Overview

This is a Django-based authentication service built using Django REST Framework. The service manages user identity verification, session management, and role-based access control.

### Architecture

The project follows Django's modular architecture:

- **accounts/** - Django app containing authentication models, views, and serializers
- **config/** - Project configuration including settings, URL routing, and WSGI/ASGI configurations
- **manage.py** - Django management script for running commands
- **requirements.txt** - Python package dependencies

### Key Components

- **accounts/models.py** - User authentication models
- **accounts/views.py** - API views for authentication endpoints
- **accounts/serialization.py** - Data serialization for API requests/responses
- **accounts/urls.py** - URL routing for authentication endpoints
- **config/settings.py** - Django project settings and configuration
- **config/urls.py** - Main URL configuration

## Project Structure

```
authentication/
├── accounts/                 # Django app for authentication
│   ├── migrations/          # Database migrations
│   ├── __init__.py
│   ├── admin.py            # Django admin configuration
│   ├── apps.py             # App configuration
│   ├── models.py           # User and auth models
│   ├── serialization.py    # API serializers
│   ├── tests.py            # Unit tests
│   ├── urls.py             # App-specific routes
│   └── views.py            # API views and authentication logic
├── config/                  # Django project configuration
│   ├── __init__.py
│   ├── asgi.py             # ASGI configuration
│   ├── settings.py         # Django settings
│   ├── urls.py             # Main URL router
│   └── wsgi.py             # WSGI configuration
├── manage.py               # Django management utility
├── requirements.txt        # Python dependencies
├── README.md               # This file
└── LICENSE                 # Project license
```

## Features

- User registration and account creation
- User login with credential validation
- Session management and authentication
- Role-based access control
- User profile management
- Password management and reset functionality
- API token-based authentication
- Audit logging of authentication events
- RESTful API design using Django REST Framework
- Database migrations for schema management

## Getting Started

### Prerequisites

- Python 3.8 or higher
- pip package manager
- Git
- SQLite (default) or other supported database

### Installation

1. Clone the repository or download the project files

2. Navigate to the project directory

3. Create a virtual environment:
   ```
   python -m venv venv
   ```

4. Activate the virtual environment:
   - Windows: `venv\Scripts\activate`
   - Linux/Mac: `source venv/bin/activate`

5. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

6. Run database migrations:
   ```
   python manage.py migrate
   ```

7. Create a superuser (admin) account:
   ```
   python manage.py createsuperuser
   ```

8. Start the development server:
   ```
   python manage.py runserver
   ```

The service will be available at `http://localhost:8000/`

## Configuration

### Environment Variables

Configure the service using environment variables:

- `DEBUG` - Set debug mode (True/False)
- `SECRET_KEY` - Django secret key for cryptographic signing
- `ALLOWED_HOSTS` - Comma-separated list of allowed hostnames
- `DATABASE_URL` - Database connection string (if using custom database)
- `CSRF_TRUSTED_ORIGINS` - CORS origins for CSRF protection

### Django Settings

Key settings in `config/settings.py`:

- **INSTALLED_APPS** - Includes `accounts` app and Django REST Framework
- **DATABASES** - Default SQLite configuration, can be modified for PostgreSQL, MySQL
- **SECRET_KEY** - Keep this secret and unique in production
- **DEBUG** - Set to False in production
- **ALLOWED_HOSTS** - Configure for your domain/IP in production
- **REST_FRAMEWORK** - Django REST Framework specific settings

### Database Configuration

Supported databases:

- SQLite (default, suitable for development)
- PostgreSQL (recommended for production)
- MySQL (also suitable for production)

To use a different database, update the `DATABASES` setting in `config/settings.py`

## API Endpoints

The API is structured around RESTful principles using Django REST Framework. All endpoints are prefixed with the accounts app URL configuration.

### Core Endpoints

**User Authentication:**
- Registration - Create new user accounts
- Login - Authenticate and obtain session/token
- Logout - End user session

**Session Management:**
- Session retrieval - Get current session details
- Session listing - View all active user sessions
- Session termination - End specific sessions

**User Profile:**
- Profile retrieval - Get user information
- Profile update - Modify user details

**Password Management:**
- Password change - Update password with verification
- Password reset - Initiate password reset flow
- Password reset confirmation - Complete reset with token

**Role and Permissions:**
- Get user roles - List assigned roles
- Check permissions - Verify access rights

All endpoints follow RESTful conventions with appropriate HTTP methods and status codes.

## Security Considerations

### General Security Practices

- Always use HTTPS in production
- Keep `SECRET_KEY` secure and unique per environment
- Never commit secrets or sensitive data to version control
- Use environment variables for sensitive configuration
- Set `DEBUG = False` in production
- Keep Django and all dependencies updated
- Use strong password hashing (Django's default PBKDF2)
- Implement CSRF protection (enabled by default)
- Use CORS headers appropriately

### Authentication Security

- Enforce strong password policies
- Implement account lockout on repeated failed attempts
- Use secure session management
- Validate all user inputs
- Hash passwords with Django's built-in authentication system
- Implement appropriate rate limiting

### Database Security

- Use parameterized queries (Django ORM does this by default)
- Restrict database access to application servers
- Regularly backup data
- Use secure database credentials
- Encrypt sensitive data in the database

## Troubleshooting

### Common Issues

**Server won't start:**
- Ensure all migrations are applied: `python manage.py migrate`
- Check database connection and credentials
- Verify `SECRET_KEY` is set in settings
- Review Django error logs for specific issues

**Database errors:**
- Run migrations: `python manage.py migrate`
- Check database permissions and connectivity
- Verify `DATABASES` configuration in settings

**Serialization errors:**
- Check model fields match serializer fields
- Verify field types and validators
- Ensure related fields are properly defined

**Authentication failures:**
- Verify user exists in database
- Check password is correct
- Ensure user is active (`is_active = True`)
- Review authentication logs

### Running Tests

Execute tests using:
```
python manage.py test
```

Run specific test file:
```
python manage.py test accounts.tests
```

### Debugging

Enable detailed logging by setting `DEBUG = True` and checking console output. Use Django's debug toolbar for development environment diagnostics.

---

## License

This project is licensed under the LICENSE file included in the repository.
