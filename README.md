# CTF Platform

A fully functional Capture The Flag (CTF) platform built with Django. This platform provides a comprehensive solution for hosting cybersecurity competitions with features like challenge management, team collaboration, real-time scoreboards, and admin tools.

## Features

### 🎯 Challenge Management

-   **Multi-category challenges**: Web, Crypto, Pwn, Rev, Forensics, Misc
-   **Rich challenge descriptions** with file attachments
-   **Progressive hints system** with point deduction
-   **Flag validation** with case-insensitive matching
-   **Admin CRUD interface** for challenge creation and management

### 👥 Team & User Management

-   **User registration and authentication**
-   **Team creation and joining** with password protection
-   **User profiles** with customizable information
-   **Role-based access control** for admins

### 🏆 Scoring & Competition

-   **Real-time scoreboard** with auto-refresh
-   **Point-based scoring system** with hint penalties
-   **Submission tracking** and attempt history
-   **User statistics** and progress visualization
-   **Team rankings** with solve time tiebreakers

### 🔧 Admin Features

-   **Comprehensive admin interface** with Django Admin
-   **Challenge import/export** capabilities
-   **User and team management** tools
-   **Submission monitoring** and statistics
-   **Cache system** for performance optimization

### 🎨 Modern UI/UX

-   **Responsive Bootstrap design**
-   **Real-time updates** with AJAX
-   **Interactive dashboards** with charts
-   **Mobile-friendly interface**
-   **Icon-rich navigation** with FontAwesome

## Quick Start

### Prerequisites

-   Python 3.8+
-   Django 4.2+
-   SQLite (default) or PostgreSQL

### Installation

1. **Clone the repository**

    ```bash
    git clone <your-repo-url>
    cd excelr8_ctf_platform
    ```

2. **Install dependencies**

    ```bash
    pip install django
    ```

3. **Set up the database**

    ```bash
    python manage.py migrate
    python manage.py populate_db  # Load sample data
    python manage.py createsuperuser  # Create admin account
    ```

4. **Run the server**

    ```bash
    python manage.py runserver
    ```

5. **Access the platform**
    - Main site: http://127.0.0.1:8000/
    - Admin panel: http://127.0.0.1:8000/admin/

### Sample Accounts

After running `populate_db`, you can use these accounts:

-   **Admin**: `admin` / `admin` (superuser)
-   **Users**: `alice`, `bob`, `charlie`, `diana` / `password123`

## Usage Guide

### For Participants

1. **Register an account** at `/register/`
2. **Create or join a team** from the user menu
3. **Browse challenges** by category or search
4. **Submit flags** and unlock hints when needed
5. **Track progress** on your profile and stats page
6. **Check rankings** on the scoreboard

### For Administrators

1. **Access admin panel** at `/admin/`
2. **Create challenges** with descriptions, files, and hints
3. **Manage teams** and user accounts
4. **Monitor submissions** and competition progress
5. **Export data** for analysis

## Configuration

### Environment Variables

For production deployment, set these environment variables:

```bash
DJANGO_SECRET_KEY=your-secret-key-here
DEBUG=False
ALLOWED_HOSTS=yourdomain.com
POSTGRES_DB=ctf_db
POSTGRES_USER=ctf_user
POSTGRES_PASSWORD=your-password
```

### Database Configuration

The platform supports both SQLite (development) and PostgreSQL (production). Update `settings.py` for production use.

### Caching

-   **Development**: Database caching (default)
-   **Production**: Redis recommended for better performance

## File Structure

```
excelr8_ctf_platform/
├── ctfd_clone/              # Django project settings
│   ├── settings.py          # Configuration
│   ├── urls.py              # URL routing
│   └── wsgi.py              # WSGI application
├── ctf/                     # Main CTF application
│   ├── models.py            # Database models
│   ├── views.py             # View logic
│   ├── admin.py             # Admin interface
│   ├── forms.py             # Form definitions
│   ├── urls.py              # URL patterns
│   ├── signals.py           # Model signals
│   ├── templates/           # HTML templates
│   └── management/          # Management commands
├── media/                   # User uploaded files
├── static/                  # Static assets
└── manage.py                # Django management script
```

## Models Overview

-   **Category**: Challenge categories (Web, Crypto, etc.)
-   **Challenge**: Main challenge model with flag and points
-   **Team**: Team model with members and scoring
-   **User**: Extended with UserProfile for additional info
-   **Submission**: Flag submission tracking
-   **Hint**: Progressive hints with point costs
-   **HintUnlock**: Tracking of hint usage
-   **ChallengeFile**: File attachments for challenges

## API Endpoints

-   `/ajax/submit-flag/` - AJAX flag submission
-   `/scoreboard/json/` - JSON scoreboard data
-   `/ajax/challenge-stats/<id>/` - Challenge statistics

## Security Features

-   **CSRF protection** on all forms
-   **User authentication** required for competition
-   **Input validation** and sanitization
-   **File upload** security measures
-   **SQL injection** protection with ORM
-   **XSS protection** with template escaping

## Performance Optimization

-   **Database caching** for leaderboards
-   **Query optimization** with select_related/prefetch_related
-   **AJAX updates** to reduce page reloads
-   **Responsive design** for fast loading
-   **Static file** optimization ready

## Development

### Adding New Challenges

1. Use admin interface or management commands
2. Include description, flag, point value, and category
3. Add hints with progressive costs
4. Attach files if needed

### Extending Functionality

-   Add new challenge categories in admin
-   Create custom management commands in `management/commands/`
-   Extend models for additional features
-   Customize templates for branding

## Deployment

### Docker (Recommended)

```dockerfile
FROM python:3.11
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
EXPOSE 8000
CMD ["gunicorn", "ctfd_clone.wsgi:application", "--bind", "0.0.0.0:8000"]
```

### Traditional Hosting

1. Set up PostgreSQL database
2. Configure environment variables
3. Collect static files: `python manage.py collectstatic`
4. Use Gunicorn + Nginx for production
5. Set up SSL certificate

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License

This project is open source and available under the MIT License.

## Support

For issues and questions:

1. Check the admin interface for configuration
2. Review Django documentation for framework issues
3. Create an issue in the repository

## Acknowledgments

Built with:

-   Django web framework
-   Bootstrap for responsive design
-   FontAwesome for icons
-   Chart.js for visualizations

---

**Ready to host your own CTF competition!** 🚀
