# COWN - Recruitment Platform

Nền tảng tuyển dụng toàn diện cạnh tranh với TopCV, được xây dựng bằng Django REST Framework.

## 🚀 Tính năng chính

### ✅ Đã hoàn thiện (115+ API endpoints)

#### 1. **Authentication & User Management** (13 endpoints)
- Đăng ký/Đăng nhập với JWT
- Xác thực email
- Quên mật khẩu
- Quản lý profile (Candidate/Employer)
- OAuth ready (Google, Facebook, LinkedIn)

#### 2. **Companies Management** (14 endpoints)
- CRUD công ty
- Quản lý thành viên (Owner, Admin, Recruiter)
- Đánh giá công ty (reviews)
- Theo dõi công ty (followers)
- Thống kê công ty
- Lọc nâng cao (size, industry, location, verified)

#### 3. **Jobs Management** (12 endpoints)
- CRUD việc làm
- Publish/Unpublish/Close jobs
- Lọc nâng cao 15+ options:
  - Mức lương, kinh nghiệm, loại hình
  - Kỹ năng, ngành nghề, địa điểm
  - Remote, urgent, featured
  - Posted within (date range)
- Thống kê việc làm

#### 4. **Applications/ATS** (16 endpoints)
- Nộp đơn ứng tuyển
- Quản lý stages (custom pipeline)
- Lên lịch phỏng vấn
- Ghi chú nội bộ
- Tracking AI match score
- Rating & screening

#### 5. **Master Data** (9 endpoints)
- Industries, Categories
- Skills, Locations
- Languages, Currencies
- Degrees, Tags, Benefits

#### 6. **Files Management** (6 endpoints)
- Upload CV/Portfolio
- Quản lý file (10MB max)
- Download files
- Lọc theo type
- AI Resume Parser ready

#### 7. **Notifications** (7 endpoints)
- 20+ loại thông báo
- Real-time notifications
- Email preferences
- Daily digest
- Mark as read
- Clear notifications

#### 8. **Saved Jobs & Alerts** (8 endpoints)
- Lưu việc làm yêu thích
- Tạo job alerts với criteria tùy chỉnh
- Tần suất: IMMEDIATE/DAILY/WEEKLY
- Toggle save/unsave
- Activate/Deactivate alerts

#### 9. **Real-time Messaging** (20+ endpoints)
- Chat 1-1 và nhóm
- Typing indicators
- Message reactions (emoji)
- File attachments
- Message threading (reply to)
- Unread count tracking
- Archive/Mute conversations
- Infinite scroll pagination

#### 10. **Analytics & Reports** (10+ endpoints)
- Dashboard tổng quan
- Job performance tracking
- Company performance analytics
- User activity tracking
- Conversion funnel analysis
- Daily statistics
- Trend analysis
- Source & device tracking

---

## 🛠 Tech Stack

### Backend
- **Django 5.2.9** - Web framework
- **Django REST Framework** - REST API
- **PostgreSQL** - Database (Aiven Cloud)
- **Redis** - Caching & Session
- **Celery** - Background tasks
- **drf-spectacular** - OpenAPI/Swagger docs

### Infrastructure
- **PostgreSQL on Aiven Cloud**
- **Redis Labs** (Free tier)
- **Celery Beat** - Scheduled tasks
- **JWT Authentication** - SimpleJWT

---

## 📦 Installation

### 1. Clone repository
```bash
git clone https://github.com/nghia87-cmd/cown.git
cd cown/backend
```

### 2. Create virtual environment
```bash
python -m venv .venv
.venv\Scripts\activate  # Windows
# source .venv/bin/activate  # Linux/Mac
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

### 4. Environment variables
Create `.env` file in `backend/` directory:
```env
# Django
SECRET_KEY=your-secret-key-here
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

# Database (Aiven PostgreSQL)
DB_NAME=defaultdb
DB_USER=avnadmin
DB_PASSWORD=your-db-password
DB_HOST=onetop-onetop.c.aivencloud.com
DB_PORT=24572

# Redis (Redis Labs)
REDIS_HOST=redis-19348.c292.ap-southeast-1-1.ec2.cloud.redislabs.com
REDIS_PORT=19348
REDIS_PASSWORD=your-redis-password
REDIS_DB=0

# Security
SECURE_SSL_REDIRECT=False
SESSION_COOKIE_SECURE=False
CSRF_COOKIE_SECURE=False
SECURE_HSTS_SECONDS=0
SECURE_HSTS_INCLUDE_SUBDOMAINS=False
SECURE_HSTS_PRELOAD=False
X_FRAME_OPTIONS=DENY
SECURE_CONTENT_TYPE_NOSNIFF=True
SECURE_BROWSER_XSS_FILTER=True
SECURE_PROXY_SSL_HEADER_ENABLED=False

# CORS
CORS_ALLOW_ALL_ORIGINS=True

# Email (for future use)
EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend
```

### 5. Run migrations
```bash
python manage.py migrate
```

### 6. Create superuser
```bash
python manage.py createsuperuser
```

### 7. Run development server
```bash
python manage.py runserver
```

---

## 📚 API Documentation

### Swagger UI
```
http://localhost:8000/api/docs/
```

### ReDoc
```
http://localhost:8000/api/redoc/
```

### OpenAPI Schema
```
http://localhost:8000/api/schema/
```

---

## 🗂 Project Structure

```
backend/
├── apps/
│   ├── authentication/     # User, JWT, OAuth
│   ├── companies/          # Company profiles
│   ├── jobs/              # Job postings
│   ├── applications/      # ATS system
│   ├── master_data/       # Reference data
│   ├── files/             # File uploads
│   ├── notifications/     # Notification system
│   ├── saved_jobs/        # Saved jobs & alerts
│   ├── messaging/         # Real-time chat
│   ├── analytics/         # Analytics & reports
│   ├── payments/          # Payment integration (TODO)
│   ├── search/            # Elasticsearch (TODO)
│   ├── recommendations/   # Job matching (TODO)
│   └── email_service/     # Email integration (TODO)
├── backend/
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
└── manage.py
```

---

## 🔥 API Endpoints Overview

### Authentication
- `POST /api/auth/register/`
- `POST /api/auth/login/`
- `POST /api/auth/logout/`
- `POST /api/auth/token/refresh/`
- `GET/PUT /api/auth/profile/`
- `POST /api/auth/change-password/`
- `POST /api/auth/password-reset/`
- `POST /api/auth/verify-email/`

### Companies
- `GET/POST /api/companies/`
- `GET/PUT/DELETE /api/companies/{id}/`
- `POST /api/companies/{id}/follow/`
- `GET /api/companies/{id}/members-list/`
- `GET /api/companies/{id}/reviews-list/`
- `GET /api/companies/{id}/stats/`

### Jobs
- `GET/POST /api/jobs/`
- `GET/PUT/DELETE /api/jobs/{id}/`
- `POST /api/jobs/{id}/publish/`
- `POST /api/jobs/{id}/close/`
- `GET /api/jobs/{id}/stats/`

### Applications
- `GET/POST /api/applications/`
- `GET/PUT /api/applications/{id}/`
- `POST /api/applications/{id}/change_status/`
- `GET/POST /api/interviews/`
- `GET/POST /api/application-notes/`

### Messaging
- `GET/POST /api/messaging/conversations/`
- `POST /api/messaging/conversations/{id}/mark_as_read/`
- `POST /api/messaging/conversations/{id}/start_typing/`
- `GET/POST /api/messaging/messages/`
- `PATCH /api/messaging/messages/{id}/edit/`
- `POST /api/messaging/messages/{id}/react/`

### Analytics
- `GET /api/analytics/dashboard/overview/`
- `GET /api/analytics/dashboard/job_performance/`
- `GET /api/analytics/dashboard/company_performance/`
- `POST /api/analytics/job-views/track/`

---

## 🚀 Next Features (TODO)

- [ ] **Payment Integration** (VNPay, Momo)
- [ ] **Email Service** (SendGrid, AWS SES)
- [ ] **Elasticsearch** - Advanced search
- [ ] **AI Resume Parser** (Affinda API)
- [ ] **Job Matching Algorithm** (ML-based)
- [ ] **WebSocket** - Real-time updates (Django Channels)

---

## 📊 Database Stats

- **85+ migrations** applied
- **12/17 apps** completed
- **115+ API endpoints**
- **PostgreSQL** on Aiven Cloud
- **Redis** for caching

---

## 🤝 Contributing

1. Fork the project
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

---

## 📝 License

This project is licensed under the MIT License.

---

## 👨‍💻 Author

**Nghia**
- GitHub: [@nghia87-cmd](https://github.com/nghia87-cmd)

---

## 🙏 Acknowledgments

Built with ❤️ using Django REST Framework
