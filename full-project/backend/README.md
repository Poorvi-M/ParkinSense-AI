# Parkinson's Audio-Based Monitoring API

## Overview

This project is a FastAPI-based backend system for monitoring and managing Parkinson's disease-related patient data using audio uploads and clinical tracking modules.

The backend provides:

* JWT authentication
* Secure audio upload handling
* Diagnosis tracking
* Disease progression monitoring
* Severity assessment
* Treatment management
* Clinical reports
* Future-ready ML integration architecture

This version contains **backend infrastructure only**.
Machine Learning inference pipelines are intentionally excluded and reserved for future integration.

---

# Tech Stack

* Python 3.11+
* FastAPI
* SQLAlchemy
* SQLite / PostgreSQL
* Pydantic
* JWT Authentication
* Uvicorn

---

# Project Structure

```text
project/
│
├── main.py
├── config.py
├── database.py
├── dependencies.py
├── auth.py
├── models.py
├── schemas.py
│
├── routes/
│   ├── auth_routes.py
│   ├── audio_routes.py
│   ├── diagnosis_routes.py
│   ├── progression_routes.py
│   ├── report_routes.py
│   ├── severity_routes.py
│   └── treatment_routes.py
│
├── services/
│   ├── audio_service.py
│   ├── diagnosis_service.py
│   ├── progression_service.py
│   ├── report_service.py
│   ├── severity_service.py
│   └── treatment_service.py
│
├── uploads/
│
├── requirements.txt
└── README.md
```

---

# Features

## Authentication

* User registration
* Secure password hashing
* JWT login authentication
* Role-based authorization
* Doctor-only protected endpoints

---

## Audio Upload System

* `.wav` and `.mp3` support
* Secure filename sanitization
* File size validation
* UUID-based collision-safe storage
* Upload status tracking
* Future ML processing hooks

---

## Diagnosis Module

* Create diagnosis records
* Update diagnosis records
* User-owned record access
* Doctor-wide access

---

## Progression Monitoring

* Track disease progression
* Progression scoring support
* Longitudinal monitoring architecture

---

## Severity Assessment

* Severity scoring support
* Severity level tracking
* Future ML integration placeholders

---

## Treatment Management

* Medication tracking
* Dosage tracking
* Treatment remarks/history

---

## Reports Module

* Clinical report management
* Doctor-accessible records
* Future PDF/report generation support

---

# Security Features

* JWT authentication
* Ownership-based access control
* Role-based authorization
* Path traversal prevention
* Secure file upload validation
* File size enforcement
* Sanitized filenames
* HTTP 404 anti-enumeration strategy

---

# Installation

## 1. Clone Repository

```bash
git clone <repository_url>
cd project
```

---

## 2. Create Virtual Environment

### Windows

```bash
python -m venv venv
venv\Scripts\activate
```

### Linux / macOS

```bash
python3 -m venv venv
source venv/bin/activate
```

---

## 3. Install Dependencies

```bash
pip install -r requirements.txt
```

---

# Environment Configuration

Create a `.env` file:

```env
SECRET_KEY=your_secret_key
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60

DATABASE_URL=sqlite:///./app.db

UPLOAD_DIR=uploads
```

---

# Running the Application

```bash
uvicorn main:app --reload
```

Server starts at:

```text
http://127.0.0.1:8000
```

---

# API Documentation

FastAPI automatically generates Swagger documentation.

## Swagger UI

```text
http://127.0.0.1:8000/docs
```

## ReDoc

```text
http://127.0.0.1:8000/redoc
```

---

# API Modules

| Module         | Purpose                        |
| -------------- | ------------------------------ |
| `/auth`        | Authentication                 |
| `/audio`       | Audio upload & tracking        |
| `/diagnosis`   | Diagnosis records              |
| `/progression` | Disease progression monitoring |
| `/severity`    | Severity assessments           |
| `/treatment`   | Treatment management           |
| `/report`      | Clinical reports               |

---

# Future ML Integration

This backend is intentionally designed to support future Machine Learning integration.

Planned future ML capabilities:

* Audio feature extraction
* Parkinson's prediction models
* Severity classification
* Disease progression analysis
* Automated report generation
* Background inference workers

ML logic is intentionally excluded from this backend-only version.

---

# Database Notes

Current setup supports:

* SQLite (development)
* PostgreSQL (recommended production)

Production deployments should use:

* Alembic migrations
* PostgreSQL
* Environment-based secrets
* Restricted CORS configuration

---

# Development Notes

## Uploads Directory

The `uploads/` folder stores uploaded audio files.

It may initially remain empty until users upload files through the API.

The directory is automatically created if it does not exist.

---

# Production Recommendations

Before production deployment:

* Replace SQLite with PostgreSQL
* Configure Alembic migrations
* Restrict CORS origins
* Store secrets securely
* Use HTTPS
* Add rate limiting
* Add logging/monitoring
* Configure background task workers

---

# Author

Backend developed for:
**Parkinson's Audio-Based Monitoring System**

---

# License

This project is intended for educational and research purposes.
