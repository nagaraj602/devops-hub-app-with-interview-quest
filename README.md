# 🚀 DevOps Knowledge Portal & Interview Hub

A production-grade, clean, responsive DevOps Knowledge Portal and Interview Hub with smooth white background styling, modular architecture, and zero database dependencies.

The application uses **https://github.com/nagaraj602/devops-hub-app-with-interview-quest.git** as its human-readable Git database for code, content, and continuous activity logs.

---

## 🌟 Key Features

### 1. 📂 Modular Architecture
Divided into decoupled files for every feature across routes, services, templates, CSS, and JS:
- **`app/routes/`**: Distinct route controllers for Question Bank, Project, Training Materials, Cheatsheet, Sync, and APIs.
- **`app/services/`**: Independent business logic for categorization, cluster sizing, tree generation, cheatsheet parsing, and continuous Git logging.
- **`app/static/css/`**: Feature-specific styles (`theme.css`, `layout.css`, `components.css`, `question_bank.css`, `project.css`, `training.css`, `cheatsheet.css`, `sync.css`).
- **`app/static/js/`**: Feature-specific client scripts (`common.js`, `question_bank.js`, `project.js`, `training.js`, `cheatsheet.js`, `sync.js`).
- **`app/templates/`**: Dedicated Jinja2 templates (`base.html`, `question_bank.html`, `project.html`, `training.html`, `cheatsheet.html`, `sync.html`, `404.html`).

### 2. 🎨 Smooth White Aesthetics & Typography Controls
- **Smooth White Styling**: Pure white (`#ffffff`) body with subtle slate borders (`#e2e8f0`) and soft card shadows.
- **Unrestricted Selection**: Users can select and copy any text anywhere across the website.
- **Dynamic Font Settings**: Real-time font size toggle (Small, Normal, Large, Extra Large) and font family toggle (Clean Sans, Monospace, Serif) saved directly in browser session storage.
- **Zero Congestion**: Fluid responsive layout eliminating awkward 2-line title wraps on mobile, tablet, or desktop screens.

### 3. 💼 Question Bank (1,269 Questions | 52 Companies | 70 Rounds | 18 Categories)
- **Top Stats Cards**: Total Companies (52), Interview Rounds (70), Total Questions (1,269), Tech Categories (18), and interactive My Favorites counter.
- **Automatic Multi-Category Recognition**:
  - `All (1269)`
  - `Behavioral (48)`
  - `Jenkins (169)`
  - `Git / GitHub (24)`
  - `General (20)`
  - `Terraform / IaC (192)`
  - `Docker (47)`
  - `AWS / Cloud (282)`
  - `Kubernetes (221)`
  - `Monitoring (57)`
  - `Linux (58)`
  - `Python (29)`
  - `Security (17)`
  - `Shell script (14)`
  - `Ansible (50)`
  - `System Design (27)`
  - `Networking (7)`
  - `CI/CD (5)`
  - `AI/ML (2)`
- **Category Filter Behavior**: Selecting any category automatically filters and expands all matching companies and rounds, while keeping answers collapsed by default.
- **Independent Expansion Controls**:
  - `Expand All` / `Collapse All`: Expands or collapses all company and round accordions.
  - `Expand Answers` / `Hide Answers`: Dedicated button to toggle all question answers at once.
- **Interactive Interview Calendar**: Month-wise interactive modal showing dates with interview rounds. Clicking a date filters to that day's interviews.
- **Live Search & Multi-Criteria Sorting**: Search across companies, rounds, questions, answers, and categories. Sort by recent (default), name (A-Z/Z-A), total questions, or interview date.

### 4. 📐 Project Page & Interactive Cluster Calculator
- Full architectural breakdown of the **Marketplace Risk & Abuse Detection Platform** (25 microservices).
- **Team Sizing Breakdown**: Full staffing model (1 dedicated DevOps team of 4 engineers, 30 developers across 5 squads, 6 QA engineers with 4 SDETs).
- **Cluster Capacity Sizing Derivation**: Mathematical derivation for 200 vCPUs across 25 microservices (recommending **18 worker nodes** of type `m6i.4xlarge` across 3 AZs for 288 vCPUs and 1,152 GB RAM with N+2 redundancy).
- **Interactive Cluster Sizing Calculator**: Dynamic sliders for CPU demand, RAM ratio, microservice count, and instance selection.

### 5. 📚 Training Materials & Notes Explorer
- **Live Hierarchy Explorer**: Left sidebar tree navigation, right content reader.
- **Default Repositories**: `artisantek/training-materials.git` and `nagaraj602/Notes.git`.
- **Custom Repositories**: Users can add any public GitHub repository (stored in browser `localStorage`).
- **Interactive Image Lightbox**:
  - Click any image inside documentation to open full-screen lightbox.
  - Close on click outside or 'X' button.
  - Zoom in/out via mouse scroll.
  - Magnifier buttons (+, -, reset) at bottom.
  - Double-click to zoom in/out.
- **Mermaid Flowcharts**: Automatic client-side rendering of architecture and workflow diagrams.
- **Collapsed Notes Answers**: Question-and-answer pairs in notes default to collapsed mode.

### 6. ⚡ Command Cheatsheet (16 Categories)
- Instant category tabs: Linux, Shell Script, Github, Build Tools, AWS, Docker, Kubernetes, Helm, Terraform, Ansible, Monitoring Tools, Shell Script Examples, K8s Manifest Files, Terraform YAML/HCL Examples, Ansible Example Files, Dockerfile Example Files.
- Instant search filter and one-click copy buttons.

### 7. 🔄 Sync All & Continuous Audit Logs
- Sync trigger buttons for individual repositories or full global sync.
- Continuous human-readable audit log persisted directly in `logs/audit_log.md` on GitHub.

---

## 🛠️ Port & Deployment

The application runs on port **8926** and uses **Ubuntu 24.04 LTS** for all stages.

### Docker Image
- **Docker Hub Target**: `nagarajkamath602/devops-hub-app-with-interview-quest:latest`
- **Multi-Stage Ubuntu Dockerfile**:
  - Stage 1: `ubuntu:24.04` builder with Python virtual environment compilation.
  - Stage 2: `ubuntu:24.04` runtime with curl, git, ca-certificates, and non-root virtualenv runtime.

### Quick Start with Docker
```bash
docker run -d --name devops-hub -p 8926:8926 nagarajkamath602/devops-hub-app-with-interview-quest:latest
```

### Quick Start with Docker Compose (Local or GCP)
```bash
docker compose up -d
```

### Deploy to Docker Desktop Kubernetes (Windows / Mac)
```bash
kubectl apply -f k8s/all-in-one.yaml
kubectl rollout status deployment/devops-hub-deployment -n devops-hub
kubectl port-forward --address 0.0.0.0 -n devops-hub svc/devops-hub-service 8926:8926
```

### Universal Deployment Script (`deploy.sh`)
```bash
bash deploy.sh
```
Options available:
1. Docker Compose deployment (port 8926)
2. Docker Desktop Kubernetes build, push & deployment (port 8926)
3. Production Kubeadm deployment
4. Standalone Docker container run (port 8926)
5. GCP automated Ubuntu VM setup
6. Cloudflare secure HTTPS tunnel (zero open ports)
7. Multi-stage image build & push

---

## 🌐 Application Endpoints (Port 8926)

| Page | URL | Description |
| :--- | :--- | :--- |
| **Question Bank** | `http://localhost:8926/question-bank` | 1,269 Questions, 52 Companies, 70 Rounds, Calendar |
| **Project Guide** | `http://localhost:8926/project` | Microservices architecture, team structure, cluster calculator |
| **Training Materials** | `http://localhost:8926/training-materials` | Live tree explorer, image lightbox, mermaid diagrams |
| **Command Cheatsheet** | `http://localhost:8926/command-cheatsheet` | 16 categories of CLI commands & manifests |
| **Sync All & Logs** | `http://localhost:8926/sync-all` | Continuous audit logs and repository sync |
| **Health Check** | `http://localhost:8926/api/health` | Service health status JSON |