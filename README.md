# IBVAP — Intelligent Border Video Analytics Platform

> **Software-driven intelligence for safer borders.**

IBVAP (Intelligent Border Video Analytics Platform) is a software-based border surveillance and video analytics platform designed to add intelligent monitoring capabilities to existing CCTV infrastructure.

Instead of replacing existing cameras with expensive proprietary smart-camera systems, IBVAP processes existing video streams through an AI-powered surveillance pipeline and converts detected security violations into evidence-backed alerts for operators.

---

## Overview

Border surveillance often relies on large networks of CCTV cameras, but continuously monitoring these feeds manually is difficult and inefficient.

IBVAP adds an intelligence layer over existing CCTV infrastructure:

```text
Existing CCTV Camera
        ↓
   Video Stream
        ↓
   Video Ingestion
        ↓
 AI / Object Detection
        ↓
 Virtual Fence & Zone Rules
        ↓
  Breach Detection
        ↓
 Evidence Snapshot
        ↓
   Security Alert
        ↓
     Database
        ↓
   FastAPI Backend
        ↓
 React Dashboard
````

The prototype demonstrates the complete workflow from video input to detection, security-rule evaluation, evidence generation, alert storage, and operator visualization.

---

# Key USP

### Turn existing CCTV cameras into intelligent surveillance systems — through software.

IBVAP is designed around:

* **Zero hardware replacement**
* **Software-based video intelligence**
* **Virtual security zones**
* **Automated breach detection**
* **Evidence-backed alerts**
* **Centralized operator dashboard**
* **Scalable architecture for multiple cameras**

This makes the system particularly suitable for environments where replacing existing CCTV infrastructure would be expensive or impractical.

---

# Core Features

## 1. Camera Management

The backend provides APIs for managing surveillance cameras.

Each camera can contain:

* Camera ID
* Name
* Location
* Video/RTSP source
* Online/offline status
* Active/inactive state

The system can also start and stop individual camera processing pipelines.

---

## 2. Video Ingestion

IBVAP uses OpenCV for video capture and processing.

The video ingestion layer:

* Reads video streams
* Extracts frames
* Processes frames for downstream computer-vision tasks
* Maintains individual processing pipelines for cameras

The prototype supports local video input for demonstration and is structured to work with IP camera streams.

---

## 3. AI / Computer Vision

The AI/CV layer performs object detection on incoming video frames.

The current prototype integrates YOLO-based object detection for relevant classes such as:

* Person
* Car
* Motorcycle
* Bus
* Truck

Detection results include information such as:

* Object class
* Confidence
* Bounding box
* Normalized coordinates
* Ground/feet point

The AI/CV module is separated from the backend rule and alert system so that the detection model can be improved independently.

---

## 4. Virtual Fence & Zone Engine

IBVAP allows operators to define virtual security boundaries over camera views.

### Polygon Zones

A polygon can represent a restricted area.

```text
+---------------------------+
|                           |
|       RESTRICTED AREA     |
|       +-------------+     |
|       |             |     |
|       |             |     |
|       +-------------+     |
|                           |
+---------------------------+
```

The system evaluates whether a detected object's position enters the defined polygon.

### Tripwire

A virtual line can be placed across a camera view.

When a detected object crosses the line, the system can generate a tripwire-crossing event.

### Target Filtering

Zones can be configured to react to:

* HUMAN
* VEHICLE
* ALL

---

## 5. Breach Detection

Object detection alone does not automatically mean that a security incident has occurred.

IBVAP combines AI detections with spatial rules.

For example:

```text
Person detected
       ↓
Check position
       ↓
Inside restricted zone?
       ↓
      YES
       ↓
Security breach
```

This allows the system to distinguish between ordinary detections and actual zone violations.

---

## 6. Evidence Generation

When a breach occurs, the system can generate an annotated evidence snapshot.

The snapshot can contain:

* Detected object
* Bounding box
* Object class
* Confidence
* Ground point
* Zone information
* Camera information
* Event timestamp

This provides visual evidence associated with the security alert.

---

## 7. Alert Management

Detected security breaches are converted into persistent alerts.

An alert contains information such as:

```text
Alert ID
Camera ID
Zone ID
Alert Type
Target Class
Confidence
Timestamp
Snapshot
Status
Message
```

Supported alert types include:

* Intrusion
* Tripwire Crossing

Alert status can be managed through the backend, allowing operators to review incidents.

---

## 8. REST API Backend

The backend is built using **Python and FastAPI**.

The API provides communication between the frontend, surveillance pipeline, and database.

Examples:

```text
GET     /api/v1/cameras/
POST    /api/v1/cameras/
PUT     /api/v1/cameras/{id}

GET     /api/v1/zones/
POST    /api/v1/zones/

GET     /api/v1/alerts/
POST    /api/v1/alerts/
PUT     /api/v1/alerts/{id}
```

The backend handles:

* Camera management
* Zone management
* Alert management
* Stream lifecycle
* Detection/rule integration
* Evidence generation
* Database persistence
* Frontend API requests

---

# System Architecture

```text
                    EXISTING CCTV
                         │
                         │
                    Video Stream
                         │
                         ▼
                ┌─────────────────┐
                │ Video Ingestion │
                │     OpenCV      │
                └────────┬────────┘
                         │
                         ▼
                ┌─────────────────┐
                │  AI / Computer  │
                │     Vision      │
                │      YOLO       │
                └────────┬────────┘
                         │
                    Detections
                         │
                         ▼
                ┌─────────────────┐
                │ Virtual Fence & │
                │   Zone Engine   │
                └────────┬────────┘
                         │
                         ▼
                ┌─────────────────┐
                │ Breach Detection│
                └────────┬────────┘
                         │
                         ▼
                ┌─────────────────┐
                │Evidence Snapshot│
                └────────┬────────┘
                         │
                         ▼
                ┌─────────────────┐
                │  Alert Service  │
                └────────┬────────┘
                         │
                         ▼
                ┌─────────────────┐
                │    Database     │
                │     SQLite      │
                └────────┬────────┘
                         │
                         ▼
                ┌─────────────────┐
                │   FastAPI REST  │
                │      APIs       │
                └────────┬────────┘
                         │
                         ▼
                ┌─────────────────┐
                │ React Dashboard │
                └─────────────────┘
```

---

# Technology Stack

## Backend

* Python
* FastAPI
* SQLAlchemy
* Pydantic
* OpenCV
* NumPy
* Ultralytics YOLO

## Database

* SQLite for the current local prototype
* SQLAlchemy ORM

The backend is structured so that the database configuration can be changed for a production deployment.

## Frontend

* React
* Vite
* JavaScript
* Leaflet / Mapbox-based visualization where applicable

## Development

* Git
* GitHub
* VS Code
* Python virtual environment
* npm

---

# Project Structure

```text
ProjectSih/
│
├── app/
│   ├── api/
│   │   └── v1/
│   │       └── endpoints/
│   │           ├── alerts.py
│   │           ├── cameras.py
│   │           ├── health.py
│   │           └── zones.py
│   │
│   ├── core/
│   │   ├── config.py
│   │   └── database.py
│   │
│   ├── models/
│   │   ├── alert.py
│   │   ├── camera.py
│   │   └── zone.py
│   │
│   ├── schemas/
│   │   ├── alert.py
│   │   ├── camera.py
│   │   └── zone.py
│   │
│   ├── services/
│   │   ├── alerts/
│   │   │   └── snapshot.py
│   │   │
│   │   └── vision/
│   │       ├── detection.py
│   │       ├── detector.py
│   │       ├── frame.py
│   │       ├── live_pipeline.py
│   │       ├── manager.py
│   │       ├── rules.py
│   │       └── stream_reader.py
│   │
│   └── main.py
│
├── scripts/
│   ├── demo_stream.py
│   ├── test_evidence_pipeline.py
│   ├── test_geometry.py
│   └── test_live_pipeline.py
│
├── tests/
│   ├── test_geometry.py
│   └── test_snapshot.py
│
├── src/
│   ├── pages/
│   │   ├── Alerts.jsx
│   │   ├── EventHistory.jsx
│   │   ├── LiveCameras.jsx
│   │   └── VirtualFence.jsx
│   ├── App.jsx
│   └── index.css
│
├── storage/
│   ├── clips/
│   ├── snapshots/
│   └── border_cctv_demo.mp4
│
├── .env.example
├── .gitignore
├── package.json
└── README.md
```

---

# Running the Project

## Backend

From the project root:

Activate the Python environment:

```bash
source .venv/bin/activate
```

Start FastAPI:

```bash
PYTHONPATH=. uvicorn app.main:app --reload
```

Backend:

```text
http://127.0.0.1:8000
```

Swagger API documentation:

```text
http://127.0.0.1:8000/docs
```

---

## Frontend

Install dependencies if required:

```bash
npm install
```

Start the frontend:

```bash
npm run dev
```

The frontend will normally be available at:

```text
http://localhost:5173
```

---

# Prototype Demonstration

The current prototype demonstrates:

1. Registering a CCTV camera
2. Starting a camera/video processing pipeline
3. Reading video frames
4. Running object detection
5. Defining virtual zones
6. Detecting polygon intrusion
7. Detecting tripwire crossing
8. Generating evidence snapshots
9. Creating persistent security alerts
10. Displaying alerts through the dashboard
11. Reviewing alert status
12. Viewing camera and event information through the frontend

---

# Backend Pipeline

The main backend processing flow is:

```text
Video Source
     ↓
StreamReader
     ↓
Frame
     ↓
Object Detection
     ↓
Zone Rule Evaluation
     ↓
Breach
     ↓
SnapshotService
     ↓
AlertService
     ↓
Database
```

The system also maintains separate camera pipelines through the stream manager.

---

# Testing

The project contains tests for the core geometry and evidence-generation components.

Current verification includes:

* Polygon point-in-polygon testing
* Tripwire intersection testing
* Target filtering
* Snapshot generation
* End-to-end live pipeline testing
* Video stream validation
* Database alert creation

Example:

```bash
pytest
```

The live pipeline can also be tested using:

```bash
PYTHONPATH=. python scripts/test_live_pipeline.py
```

---

# Team Contributions

IBVAP is developed as a multi-member system.

### Backend / Systems

Responsible for:

* FastAPI backend
* REST APIs
* Database models
* Camera management
* Video ingestion
* Stream management
* Virtual-fence rule engine
* Breach-to-alert pipeline
* Evidence generation
* Frontend ↔ Backend integration

### AI / Computer Vision

Responsible for:

* Object detection
* Computer-vision models
* Detection/tracking development
* AI/CV-side integration

### Frontend

Responsible for:

* React dashboard
* Camera monitoring interface
* Alerts interface
* Event history
* Virtual-fence interface
* Operator experience

### DevOps / Infrastructure

Responsible for:

* Deployment
* Containerization
* Infrastructure
* CI/CD
* Operational setup

---

# Why IBVAP?

Traditional surveillance systems often require operators to continuously monitor many camera feeds.

IBVAP aims to reduce this dependency by automatically identifying relevant events.

Instead of:

```text
Hundreds of CCTV feeds
        ↓
Continuous manual monitoring
        ↓
Operator notices incident
        ↓
Manual investigation
```

IBVAP provides:

```text
CCTV feeds
     ↓
AI detection
     ↓
Security-zone analysis
     ↓
Automatic breach detection
     ↓
Evidence
     ↓
Actionable alert
```

This allows operators to focus their attention on events that require investigation.

---

# Key Advantages

### Software-Driven

Uses existing CCTV infrastructure rather than requiring complete camera replacement.

### Cost-Effective

Reduces the need for specialized smart-camera hardware.

### Rapid Deployment

Can be layered over existing video infrastructure.

### Configurable

Virtual fences and restricted areas can be configured according to surveillance requirements.

### Evidence-Based

Security events are accompanied by stored evidence snapshots.

### Scalable Architecture

The backend is designed around independent camera processing pipelines and REST APIs.

---

# Current Prototype Scope

The current prototype focuses on the core surveillance workflow:

**Camera → Video → AI Detection → Zone Rules → Breach → Evidence → Alert → Dashboard**

Advanced production capabilities such as large-scale command-center synchronization, advanced model optimization, tamper-evident event logging, and additional computer-vision modules can be added as future extensions.

---

# Future Enhancements

Potential future extensions include:

* Advanced object tracking
* ANPR / license-plate recognition
* Face detection and recognition where legally and operationally appropriate
* Low-light enhancement
* Model optimization for edge hardware
* Tamper-evident event logs
* Distributed command-center synchronization
* Advanced analytics and reporting
* Multi-site deployment
* Production-grade PostgreSQL deployment
* Edge-device optimization
* Automated incident escalation

---

# Project Vision

IBVAP aims to move border surveillance from passive video monitoring toward intelligent, event-driven situational awareness.

> **From Surveillance to Situational Awareness — Safer Borders, Stronger Nation.**

---
