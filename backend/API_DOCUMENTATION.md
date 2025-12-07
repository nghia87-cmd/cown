# COWN - Nền Tảng Tuyển Dụng

## 🚀 Tổng Quan

COWN là một nền tảng tuyển dụng toàn diện, cạnh tranh với TopCV và các nền tảng khác, được xây dựng với Django REST Framework.

## 📊 Thống Kê Dự Án

- **Database**: PostgreSQL (Aiven Cloud)
- **Cache/Queue**: Redis Labs
- **Migrations**: 75+ migrations applied
- **API Endpoints**: ~60+ endpoints
- **Apps**: 17 Django apps

## 🏗️ Kiến Trúc

### Core Apps
1. **Authentication** (`apps/authentication/`)
   - JWT-based authentication
   - Social auth support (Google, LinkedIn)
   - Email verification
   - Password reset

2. **Companies** (`apps/companies/`)
   - Company profiles
   - Company members & roles
   - Company reviews
   - Company followers

3. **Jobs** (`apps/jobs/`)
   - Job posting management
   - Advanced search & filtering
   - Job statistics
   - Screening questions

4. **Applications/ATS** (`apps/applications/`)
   - Application tracking
   - Interview scheduling
   - Application stages/pipeline
   - Notes & activities

5. **Master Data** (`apps/master_data/`)
   - Industries, Job Categories
   - Skills, Locations
   - Languages, Currencies
   - Degrees, Tags, Benefits

### Feature Apps

6. **Files** (`apps/files/`) ✨ NEW
   - Resume/CV upload
   - Company logos & cover images
   - File validation (max 10MB)
   - Supported: PDF, DOC, DOCX, JPG, PNG, GIF

7. **Notifications** (`apps/notifications/`) ✨ NEW
   - Real-time notifications
   - Email notifications
   - Notification preferences
   - 20+ notification types

8. **Saved Jobs** (`apps/saved_jobs/`) ✨ NEW
   - Bookmark jobs
   - Job alerts with custom criteria
   - Alert frequencies (immediate, daily, weekly)

## 📡 API Documentation

### Base URL
```
http://localhost:8000/api/
```

### Interactive Documentation
- **Swagger UI**: http://localhost:8000/api/docs/
- **ReDoc**: http://localhost:8000/api/redoc/
- **OpenAPI Schema**: http://localhost:8000/api/schema/

## 🔐 Authentication Endpoints

```
POST   /api/auth/register/              - Register new user
POST   /api/auth/login/                 - Login
POST   /api/auth/logout/                - Logout
POST   /api/auth/refresh/               - Refresh JWT token
POST   /api/auth/verify-email/          - Verify email
POST   /api/auth/resend-verification/   - Resend verification
POST   /api/auth/password/reset/        - Request password reset
POST   /api/auth/password/reset/confirm/ - Confirm password reset
GET    /api/auth/profile/               - Get current user profile
PUT    /api/auth/profile/               - Update profile
POST   /api/auth/password/change/       - Change password
POST   /api/auth/check-email/           - Check if email exists
POST   /api/auth/social/                - Social auth
```

## 🏢 Companies Endpoints

```
GET    /api/companies/                  - List companies (with filters)
POST   /api/companies/                  - Create company
GET    /api/companies/{id}/             - Get company details
PUT    /api/companies/{id}/             - Update company
DELETE /api/companies/{id}/             - Delete company
POST   /api/companies/{id}/follow/      - Follow company
POST   /api/companies/{id}/unfollow/    - Unfollow company
GET    /api/companies/{id}/stats/       - Company statistics

# Company Members
GET    /api/companies/members/          - List members
POST   /api/companies/members/          - Add member
PUT    /api/companies/members/{id}/     - Update member
DELETE /api/companies/members/{id}/     - Remove member

# Company Reviews
GET    /api/companies/reviews/          - List reviews
POST   /api/companies/reviews/          - Create review
PUT    /api/companies/reviews/{id}/     - Update review
DELETE /api/companies/reviews/{id}/     - Delete review
```

### Company Filters
- `search` - Search in name/description
- `city`, `province`, `country` - Location filters
- `industry` - Filter by industry UUID
- `size` - Company size (STARTUP, SMALL, MEDIUM, LARGE, ENTERPRISE)
- `is_verified` - Verified companies only
- `is_featured` - Featured companies
- `has_active_jobs` - Companies with active jobs

## 💼 Jobs Endpoints

```
GET    /api/jobs/                       - List jobs (with advanced filters)
POST   /api/jobs/                       - Create job
GET    /api/jobs/{id}/                  - Get job details
PUT    /api/jobs/{id}/                  - Update job
DELETE /api/jobs/{id}/                  - Delete job
POST   /api/jobs/{id}/publish/          - Publish job
POST   /api/jobs/{id}/unpublish/        - Unpublish job
POST   /api/jobs/{id}/close/            - Close job
GET    /api/jobs/{id}/stats/            - Job statistics
GET    /api/jobs/my-company-jobs/       - Jobs of my companies
```

### Job Filters (Advanced)
- `search` - Full-text search
- `city`, `province`, `country` - Location
- `is_remote` - Remote jobs only
- `job_type` - FULL_TIME, PART_TIME, CONTRACT, INTERNSHIP, FREELANCE
- `experience_level` - INTERN, ENTRY, JUNIOR, MIDDLE, SENIOR, LEAD, EXECUTIVE
- `min_salary`, `max_salary` - Salary range
- `salary_currency` - Currency code
- `category` - Job category UUID
- `industry` - Industry UUID
- `skills` - Comma-separated skills
- `company` - Company UUID
- `company_size` - Company size filter
- `verified_company` - From verified companies only
- `is_featured`, `is_urgent` - Featured/urgent jobs
- `posted_within` - Posted within N days
- `expires_after` - Jobs expiring after date
- `status` - DRAFT, PENDING, ACTIVE, PAUSED, CLOSED, EXPIRED
- `education_level` - Required education level

## 📝 Applications/ATS Endpoints

```
# Applications
GET    /api/applications/               - List applications
POST   /api/applications/               - Submit application
GET    /api/applications/{id}/          - Get application details
PUT    /api/applications/{id}/          - Update application
DELETE /api/applications/{id}/          - Delete application
POST   /api/applications/{id}/withdraw/ - Withdraw application

# Application Stages
GET    /api/stages/                     - List stages
POST   /api/stages/                     - Create stage
PUT    /api/stages/{id}/                - Update stage
DELETE /api/stages/{id}/                - Delete stage

# Interviews
GET    /api/interviews/                 - List interviews
POST   /api/interviews/                 - Schedule interview
PUT    /api/interviews/{id}/            - Update interview
DELETE /api/interviews/{id}/            - Delete interview
POST   /api/interviews/{id}/complete/   - Mark as completed
POST   /api/interviews/{id}/cancel/     - Cancel interview

# Application Notes
GET    /api/notes/                      - List notes
POST   /api/notes/                      - Create note
PUT    /api/notes/{id}/                 - Update note
DELETE /api/notes/{id}/                 - Delete note
```

## 🗂️ Master Data Endpoints

```
GET    /api/master/industries/          - List industries
GET    /api/master/categories/          - List job categories
GET    /api/master/skills/              - List skills
GET    /api/master/locations/           - List locations
GET    /api/master/languages/           - List languages
GET    /api/master/currencies/          - List currencies
GET    /api/master/degrees/             - List education degrees
GET    /api/master/tags/                - List tags
GET    /api/master/benefits/            - List benefits
```

## 📁 Files Endpoints ✨ NEW

```
GET    /api/files/                      - List user's files
POST   /api/files/                      - Upload file
GET    /api/files/{id}/                 - Get file details
DELETE /api/files/{id}/                 - Delete file
GET    /api/files/{id}/download/        - Get download URL
GET    /api/files/resumes/              - Get all resumes
```

### File Types
- RESUME, COVER_LETTER, PORTFOLIO
- COMPANY_LOGO, COMPANY_COVER
- PROFILE_PICTURE, DOCUMENT, OTHER

### File Filters
- `file_type` - Filter by type
- `search` - Search in filename/description

## 🔔 Notifications Endpoints ✨ NEW

```
GET    /api/notifications/              - List notifications
GET    /api/notifications/{id}/         - Get notification
POST   /api/notifications/{id}/mark_as_read/ - Mark as read
POST   /api/notifications/mark_all_as_read/ - Mark all as read
GET    /api/notifications/unread/       - Get unread only
GET    /api/notifications/unread_count/ - Count unread
DELETE /api/notifications/clear_all/    - Delete all read

# Preferences
GET    /api/notifications/preferences/  - Get preferences
PUT    /api/notifications/preferences/  - Update preferences
```

### Notification Types
- Application: RECEIVED, REVIEWED, ACCEPTED, REJECTED
- Interview: SCHEDULED, REMINDER, CANCELLED
- Job: POSTED, EXPIRED, MATCH, ALERT
- Company: FOLLOWED, UPDATE, NEW_JOB
- System: ALERT, ACCOUNT_UPDATE

## 🔖 Saved Jobs Endpoints ✨ NEW

```
GET    /api/jobs/saved/                 - List saved jobs
POST   /api/jobs/saved/                 - Save a job
DELETE /api/jobs/saved/{id}/            - Unsave job
POST   /api/jobs/saved/toggle/          - Toggle save status
GET    /api/jobs/saved/check/           - Check if job is saved

# Job Alerts
GET    /api/jobs/alerts/                - List job alerts
POST   /api/jobs/alerts/                - Create alert
PUT    /api/jobs/alerts/{id}/           - Update alert
DELETE /api/jobs/alerts/{id}/           - Delete alert
POST   /api/jobs/alerts/{id}/activate/  - Activate alert
POST   /api/jobs/alerts/{id}/deactivate/ - Deactivate alert
```

## 🔧 Setup & Installation

### Prerequisites
- Python 3.12+
- PostgreSQL
- Redis

### Installation Steps

1. **Clone & Setup Environment**
```bash
cd backend
python -m venv .venv
.venv\Scripts\activate  # Windows
pip install -r requirements.txt
```

2. **Configure Environment**
Create `.env` file with database credentials, Redis, email settings, etc.

3. **Run Migrations**
```bash
python manage.py migrate
```

4. **Create Superuser**
```bash
python manage.py createsuperuser
```

5. **Run Server**
```bash
python manage.py runserver
```

6. **Run Celery (Optional)**
```bash
celery -A backend worker -l info
celery -A backend beat -l info
```

## 📦 Key Features

### ✅ Implemented
- JWT Authentication with refresh tokens
- Company management with members & roles
- Advanced job posting with screening questions
- Full ATS (Applicant Tracking System)
- Interview scheduling
- File uploads (resumes, images)
- Real-time notifications
- Email notifications
- Job alerts with custom criteria
- Saved jobs
- Advanced search & filtering
- Master data management
- API documentation (Swagger/ReDoc)

### 🔄 Planned Features
- AI Resume Parser (Affinda integration)
- Job matching algorithm
- Real-time chat (WebSocket)
- Payment gateway integration
- Elasticsearch integration
- Analytics & reporting dashboard
- Admin panel enhancements

## 🗄️ Database Schema

### Core Tables
- users, companies, jobs, applications
- company_members, company_reviews, company_followers
- interviews, application_stages, application_notes
- job_skills, job_questions
- uploaded_files, notifications
- saved_jobs, job_alerts

### Master Data Tables
- industries, job_categories, skills
- locations, languages, currencies
- degrees, tags, benefits

## 🎯 Performance Optimizations

- Database indexing on frequently queried fields
- `select_related()` and `prefetch_related()` for reducing queries
- Redis caching for frequently accessed data
- Pagination on list endpoints
- Denormalized stats (job_count, application_count)

## 🔒 Security Features

- JWT with token blacklist
- Password hashing (bcrypt)
- Email verification
- CORS configuration
- SSL/HTTPS support
- Rate limiting (planned)
- Input validation & sanitization

## 📊 Monitoring & Logging

- Sentry integration for error tracking
- Structured logging to files
- Database query logging
- API endpoint logging

## 🧪 Testing

```bash
# Run all tests
python manage.py test

# Run specific app tests
python manage.py test apps.jobs
```

## 📝 Notes

- PostgreSQL database hosted on Aiven Cloud
- Redis hosted on Redis Labs (free tier, DB 0 only)
- Media files stored locally in development
- S3/MinIO ready for production

## 👥 Team

Phát triển bởi: [Your Name]

## 📄 License

[Add your license here]
