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

# License

This project is intended for educational and research purposes.
