import os
import re
from pathlib import Path
from typing import Dict, Any, List, Optional
from app.config import PROJECT_FILE

try:
    import markdown
except ImportError:
    class _MockMarkdown:
        @staticmethod
        def markdown(text, **kwargs):
            return text.replace("\n", "<br>")
    markdown = _MockMarkdown()

def render_md(text: str) -> str:
    if not text:
        return ""
    try:
        return markdown.markdown(text, extensions=['fenced_code', 'tables', 'nl2br'])
    except Exception:
        return markdown.markdown(text)

ADDITIONAL_PROJECT_QUESTIONS = [
    {
        "id": "proj_q_team_structure",
        "question": "How many DevOps teams, developers, QA, and testers were there on the project?",
        "short_answer": "1 Dedicated Platform/DevOps Team (4 Engineers), ~30 Developers across 5 domain squads, and 6 QA Engineers (4 SDETs + 2 Functional/Abuse testers), totaling ~42 engineering members.",
        "detailed_answer": """
### 👥 Engineering & DevOps Team Organization

Our engineering organization followed a Spotify-inspired squad model with cross-functional domain teams supported by a centralized Platform/DevOps team:

#### 1. DevOps & Platform Engineering Team (1 Centralized Team - 4 Engineers)
* **1 Lead DevOps / Cloud Architect:** Owned overall cloud architecture on AWS (EKS, VPC networking, IAM security boundaries, Terraform module governance, and GitOps release compliance).
* **2 Senior DevOps Engineers:** Designed and maintained end-to-end Jenkins Shared Library pipelines, Helm charts, Docker image security scanning (Trivy), Prometheus/Grafana observability, Kafka consumer lag scaling, and EKS Cluster autoscaling policies.
* **1 Associate / Automation Engineer:** Handled Jira day-to-day tickets, developer branch access permissions, secret management in AWS Secrets Manager / Vault, patch schedules, and pipeline failure triage.

#### 2. Development Squads (~30 Software Engineers across 5 Squads)
Each squad had 5–7 developers (primarily Go and Java/Spring Boot for microservices, plus React for the Trust & Safety Analyst console) along with an embedded Tech Lead:
* **Squad 1 - Ingestion & Streaming (5 Devs):** Handled Kafka event ingestion, schema registry normalization, and deduplication of listing, order, and review streams.
* **Squad 2 - Velocity Rule Engine (6 Devs):** Built low-latency stateful rule evaluation services using Redis in-memory sliding windows.
* **Squad 3 - Anomaly Scoring & Graph Analytics (6 Devs):** Developed machine learning scoring wrappers and Neo4j entity graph link-analysis microservices.
* **Squad 4 - Case Queue & Trust Analyst Portal (7 Devs):** Built the workflow management engine, analyst review dashboard, and SLA assignment queues.
* **Squad 5 - Enforcement & Third-Party Integrations (6 Devs):** Developed webhook handlers and transactional dispatchers calling marketplace APIs for seller suspension, listing takedowns, and payout holds.

#### 3. Quality Assurance & Testing Team (6 QA Engineers)
* **4 SDETs (Automation Engineers):** Wrote contract tests (Pact), end-to-end API automation suites (REST Assured / PyTest), and load/stress test scripts using k6 and JMeter integrated directly into Jenkins PR validation pipelines.
* **2 Manual & Functional QA Specialists:** Focused on exploratory risk-scenario testing, simulating sophisticated fraud rings, adversarial review patterns, and verifying edge-case analyst override workflows.

#### 4. Product & Leadership Alignment
* **2 Product Managers** (1 Risk & Seller Policy PM, 1 Trust Platform PM)
* **1 Agile Scrum Master**
* **1 Engineering Manager**
""",
        "detailed_answer_html": ""
    },
    {
        "id": "proj_q_cluster_sizing",
        "question": "How many nodes were there in the cluster for these 25 microservices? (Takes 200 CPU for these microservices — decide how many nodes and RAM is needed).",
        "short_answer": "18 Worker Nodes of type m6i.4xlarge (16 vCPUs, 64 GB RAM each) distributed across 3 Availability Zones (6 nodes/AZ) providing 288 total vCPUs and 1,152 GB RAM with N+2 redundancy.",
        "detailed_answer": """
### 🖥️ Cluster Capacity Planning & Sizing Derivation

#### 1. Baseline Workload Requirements
* **Microservices Count:** 25 microservices (each running 2 to 6 pod replicas for high availability and load distribution).
* **Workload CPU Demand:** **200 vCPUs** (total container CPU resource requests across all 25 microservices).
* **Workload RAM Demand:** 
  * Microservices written in Java (Spring Boot) and stateful stream processing engines require ~3 GB to 4 GB RAM per CPU core to prevent garbage collection pauses.
  * Go microservices require ~1.5 GB to 2 GB RAM per core.
  * Weighted average memory footprint = **3.5 GB to 4 GB RAM per vCPU**.
  * Total workload memory request = 200 vCPUs × 3.5 GB = **~700 GB to 800 GB RAM**.

#### 2. System Overhead & Kubernetes DaemonSets
Each Kubernetes worker node requires system and daemon reservations:
* Kubelet, OS kernel, and systemd: ~1 vCPU, ~2 GB RAM.
* DaemonSets running on every node:
  * AWS VPC CNI (`aws-node`)
  * `kube-proxy`
  * CoreDNS / NodeLocal DNSCache
  * Prometheus Node-Exporter
  * Fluentbit / Datadog Log Shipper
  * Falco / Trivy runtime security sensor
* Total overhead per node: ~1.5 to 2 vCPUs and ~4 to 6 GB RAM.

#### 3. Worker Node Instance Type Selection
We evaluated AWS EC2 instance families:
* **Option A: `c6i.4xlarge` (16 vCPUs, 32 GB RAM):** Insufficient memory-to-CPU ratio (2:1). JVM services would suffer OOMKilled errors.
* **Option B: `m6i.8xlarge` (32 vCPUs, 128 GB RAM):** 9 nodes total. While CPU/RAM fit, having only 3 nodes per AZ creates a large blast radius if a node crashes.
* **Selected Best Practice: `m6i.4xlarge` (16 vCPUs, 64 GB RAM, 12.5 Gbps Network Bandwidth):**
  * Raw capacity per node: 16 vCPUs, 64 GB RAM.
  * Allocatable capacity for application pods after OS & DaemonSets: **~14 vCPUs** and **~58 GB RAM**.

#### 4. Node Count Calculation & High Availability (HA) Buffer
* **Raw Nodes Needed for Workload:** 200 vCPUs ÷ 14 allocatable vCPUs/node = **14.28 ≈ 15 nodes**.
* **Memory Check:** 15 nodes × 58 GB = 870 GB allocatable RAM (sufficient for the 700–800 GB workload demand).
* **Resilience, Rolling Updates & Multi-AZ Distribution:**
  * To guarantee high availability, workloads are balanced equally across **3 Availability Zones** (`us-east-1a`, `us-east-1b`, `us-east-1c`).
  * We add **1 spare node per AZ** (N+2 redundancy across the cluster). This ensures that if an entire node fails or is drained during a Kubernetes version upgrade, no pod encounters scheduling delays.
  * **Final Total Worker Nodes:** **18 Nodes** (6 nodes per AZ).

#### 5. Total Provisioned Cluster Capacity & Headroom
* **Total Provisioned vCPUs:** 18 nodes × 16 vCPUs = **288 vCPUs** (Workload uses ~70% baseline capacity, leaving 30% headroom for flash sale spikes before Cluster Autoscaler spawns new EC2s).
* **Total Provisioned Memory:** 18 nodes × 64 GB = **1,152 GB (1.15 TB) RAM**.
* **Storage / EBS:** Each node attached to 150 GB gp3 volume (3,000 IOPS, 125 MB/s throughput) for root filesystem and local container image caching.

#### 6. Node Pool Segmentation
The 18 nodes are divided into specialized EKS managed node groups using Kubernetes labels and taints:
* **Node Group 1 (Ingestion & Detection - 8 Nodes):** Dedicated to Kafka consumer microservices and Rule Engines with aggressive HPA scaling tied to Kafka lag metrics.
* **Node Group 2 (Core Business Microservices - 6 Nodes):** General microservices (Scoring, Risk Aggregation, Case Queues).
* **Node Group 3 (Analyst Portal & Enforcement - 4 Nodes):** Frontends, reporting jobs, and outbound webhook dispatchers.
""",
        "detailed_answer_html": ""
    }
]

# Pre-render markdown for additional questions
for q in ADDITIONAL_PROJECT_QUESTIONS:
    q["detailed_answer_html"] = render_md(q["detailed_answer"])

class ProjectService:
    def __init__(self, project_path: Optional[str] = None):
        self.project_file = Path(project_path or PROJECT_FILE)

    def get_project_data(self) -> Dict[str, Any]:
        return {
            "title": "E-Commerce - Marketplace Risk Detection Platform",
            "guide_badge": "Project Architecture & Guide",
            "overview_paragraphs": [
                "The project involved building a Marketplace Seller Risk & Abuse Detection Platform for a large online marketplace connecting third-party sellers with buyers. As the platform scaled to tens of thousands of sellers and millions of listings, it became a target for fake listings, review manipulation, seller account takeovers, and abuse ratings using networks of fake accounts.",
                "The platform continuously ingests signals from listing creation, seller account activity, orders, and reviews, detects suspicious patterns in near real-time, routes high-confidence cases for automated action and lower-confidence cases to a trust & safety analyst queue, and triggers enforcement actions (seller suspension, listing takedown, payout holds) through the marketplace's existing systems.",
                "It was designed using a microservices architecture to allow independent scaling of ingestion, detection, and case-management workloads."
            ],
            "microservices": [
                {"name": "Event Ingestion Service", "desc": "Consumes events from marketplace Kafka topics (listings, seller accounts, orders, reviews) and normalizes them into an internal schema."},
                {"name": "Signal Enrichment Service", "desc": "Adds contextual data like device fingerprinting, IP geolocation, and seller account history to incoming events."},
                {"name": "Entity Graph Service", "desc": "Maintains a graph of relationships between sellers, devices, payment methods, and addresses to surface hidden links between related accounts."},
                {"name": "Velocity Rule Engine Service", "desc": "Evaluates real-time rules against event streams (e.g., listings-per-hour thresholds, multiple accounts sharing a device)."},
                {"name": "Anomaly Scoring Service", "desc": "Generates a statistical anomaly score based on seller/account behavior, feeding in as a signal alongside rule outputs."},
                {"name": "Risk Aggregation Service", "desc": "Combines rule hits and anomaly scores into a risk score per entity and determines routing (auto-action, analyst review, or dismiss)."},
                {"name": "Case Queue Service", "desc": "Maintains the prioritized queue of flagged entities awaiting analyst review, with SLA-based aging."},
                {"name": "Enforcement Orchestration Service", "desc": "Converts confirmed decisions into calls to the marketplace's existing seller/listing APIs (suspension, takedown, payout hold), with retry handling."}
            ],
            "tools_and_tech": [
                {"name": "Kubernetes", "desc": "For container orchestration and independent autoscaling of ingestion, detection, and case-management workloads."},
                {"name": "Jenkins", "desc": "For CI/CD pipelines, including canary rollouts for rule/config changes."},
                {"name": "Kafka", "desc": "Backbone for consuming marketplace events and internal service communication, partitioned by seller ID."},
                {"name": "Prometheus & Grafana", "desc": "For monitoring detection latency, queue depth, false-positive rate, and Kafka consumer lag."},
                {"name": "ELK Stack", "desc": "For centralized logging and audit trails."},
                {"name": "Distributed Databases (MongoDB, Redis, Neo4j)", "desc": "Used across services based on access pattern: case data, real-time velocity counters, and entity relationship graphs respectively."},
                {"name": "Java / Go", "desc": "Backend languages used for the microservices."}
            ],
            "key_results": [
                "Reduced average time-to-detection for abusive seller activity from days to under 10 minutes for high-confidence automated cases.",
                "Cut manual review workload for the trust & safety team by an estimated 60%.",
                "Reduced fake listing and review manipulation incidents, improving buyer trust metrics.",
                "Improved detection pipeline stability during peak sale events through better autoscaling and Kafka partition tuning."
            ],
            "anticipated_follow_ups": [
                {
                    "question": "How did you handle scaling during peak events like flash sales?",
                    "answer": "We ran ingestion and detection services in a separate node pool with Horizontal Pod Autoscaling tied to Kafka consumer lag rather than just CPU, and over-provisioned Kafka partitions ahead of known peak events."
                },
                {
                    "question": "How did you deploy rule changes safely, given the risk of false positives?",
                    "answer": "Rule changes went through Jenkins pipelines that ran them against shadow traffic first, comparing flag rates against production before promoting, with automated rollback if false-positive rate SLOs were breached."
                },
                {
                    "question": "How did the platform avoid becoming a single point of failure for enforcement actions?",
                    "answer": "The Enforcement Orchestration Service only made outbound calls to existing seller/listing APIs. If those were unavailable, we queued actions with retry/backoff rather than blocking the detection pipeline."
                }
            ],
            "prep_questions": [
                {
                    "id": "prep_intro",
                    "number": 1,
                    "title": "1. Introduction",
                    "subtitle": "Tell me about yourself / your background / day-to-day responsibilities",
                    "content_html": render_md("""
*Use this response when the interviewer asks variations of:*
• *Tell me about yourself / your background*
• *Walk me through your resume or profile*
• *What are your day-to-day responsibilities?*
• *Walk me through your DevOps experience*

I am Nagaraj, and I currently work as a DevOps Engineer. My primary focus is on automating the deployment and management of software applications, and I work with a wide variety of tools and technologies to make that happen.

I have hands-on experience with **Jenkins**, our CI/CD tool, which takes source code from developers and deploys it into different environments. I've also worked extensively with **Git** for source code management, creating repositories, managing branches, merging code, and resolving merge conflicts. In my team, I also take on the Admin role for both Git and Jenkins, so I handle a good share of tickets specifically related to these tools, including branching strategy, creating and deleting branches, and merge-related issues.

On the cloud side, I manage and maintain infrastructure on **AWS**, working with services like EC2, S3, VPC, Load Balancing, Auto Scaling, CloudWatch, CloudTrail, and IAM.

I'm responsible for our containerization stack, primarily **Docker and Kubernetes**. I've written Dockerfiles and optimized them using multi-stage builds to reduce image size. For deploying and managing applications on Kubernetes, I use **Helm** to package and template our workloads, which makes deployments more consistent and easier to manage across environments.

I've worked with **Terraform** to provision infrastructure as code on AWS, and I use **Ansible** as our configuration management tool.

#### Day-to-Day Responsibilities
Day to day, most of my work revolves around resolving tickets, mainly around build issues, deployment issues, Git issues, and Jenkins issues. Jira is our ticketing tool, and we prioritize tickets based on severity. Some are critical and need to be closed within a few hours. Alongside ticket work, I also focus on automation, which is an ongoing effort since there's always something that can be automated or improved.
""")
                },
                {
                    "id": "prep_project",
                    "number": 2,
                    "title": "2. Explain your Project",
                    "subtitle": "Can you walk me through the key components and architecture of your project?",
                    "content_html": render_md("""
I am currently working on an e-commerce project where we are developing a large-scale **Marketplace Seller Risk & Abuse Detection Platform**. The platform continuously ingests signals across listings, seller activity, orders, and reviews to detect and mitigate fraudulent patterns and abuse in near real-time.

In this project, I primarily handle the DevOps side of things. This includes managing the CI/CD pipeline end-to-end, starting from Git and going all the way through to deployment on AWS EKS.

I provision infrastructure using **Terraform**, and for any patching or configuration management needs, we use **Ansible**. For monitoring, we rely on **Prometheus and Grafana** for metrics, along with the **ELK stack** for logging.
""")
                },
                {
                    "id": "prep_cicd",
                    "number": 3,
                    "title": "3. Explain your CI/CD strategy",
                    "subtitle": "How do you handle continuous integration and continuous deployment?",
                    "content_html": render_md("""
For this project, our CI/CD pipeline is built using **Jenkins** and covers the complete flow, starting from a developer raising a PR to final deployment on EKS. We maintain two pipelines per repo (a PR pipeline for validation and a deployment pipeline for build and release) built using a **Shared Library** approach, so common logic like Git checkout, Docker builds, Trivy scans, and Helm-based deployments is reused across projects instead of duplicated per repo.

#### CI Pipeline (Pre-Merge Quality Gate)
The CI pipeline runs on every PR into dev, staging, or master, acting as our pre-merge quality gate. It starts with a Git checkout, followed by unit tests and static code analysis using SonarQube with a quality gate that hard-fails on code quality issues. Once Sonar passes, we build the Docker image locally without pushing it to ECR, then run **Trivy** scans across the filesystem, Dockerfile configuration, and the built image, gating on Critical and High severity vulnerabilities. If any check fails, the developer fixes the code on their feature branch and re-raises the PR. This gate runs consistently across all three branches, since it also catches new vulnerabilities surfacing between promotions, not just new code changes.

Pipeline status is reported back to GitHub directly on the PR for quick feedback, and every PR also requires approval from two admins before merging, ensuring senior oversight across the pipeline.

#### CD Pipeline (Deployment Pipeline)
The CD pipeline runs after a PR is approved and merged, handling build and deployment. It builds the Docker image, pushes it to Amazon ECR, updates our Helm chart values, and deploys to the environment corresponding to the branch.

* **On merge to `dev`:** The pipeline auto-deploys to a lower environment for QA testing.
* **On merge to `staging`:** Auto-deployed to UAT for integration testing across the full microservice flow.
* **On merge to `master`:** The deployment pipeline runs up to production but pauses at a manual input step, requiring explicit confirmation before it proceeds, giving us a controlled release window rather than continuous auto-deployment to prod.

#### Centralized Scanning Pipeline
We also have a centralized scanning pipeline that runs scans across all our images and repositories independently of the build pipeline. Results are aggregated into a central vulnerability management platform, giving us consistent visibility across projects instead of results being scattered across individual Jenkins jobs. This provides severity-based triage, ownership assignment, and ticket creation for tracking remediation, while keeping our build pipeline fast and lightweight.
""")
                },
                {
                    "id": "prep_branching",
                    "number": 4,
                    "title": "4. Explain your Branching Strategy",
                    "subtitle": "What branching strategy do you use for version control and why?",
                    "content_html": render_md("""
We follow a robust branching strategy with **`dev`**, **`staging`**, and **`master`** as our primary long-lived branches, with all feature work happening in short-lived feature branches created off `dev`.

#### 1. Feature Development
When a developer picks up a ticket, they create a feature branch off `dev` (e.g. `feature/JIRA-101-auth-v2`), write and commit their code locally, and test it in their own local container environment. Once ready, they raise a PR back into `dev`.

#### 2. Pre-Merge Gate & Senior Approval
Every PR into `dev` goes through an automated pre-merge gate consisting of unit tests, SonarQube analysis for code quality, and a lightweight Trivy container scan gating on Critical and High severity vulnerabilities. In addition, every PR requires approval from **two admins** before it can be merged, ensuring strict code quality and architectural governance.

#### 3. DEV Branch (Microservice Isolation Testing)
Once merged into `dev`, our Jenkins deployment pipeline automatically deploys the service to the DEV environment, where QA tests the microservice in isolation.

#### 4. Staging Branch (UAT End-to-End Integration)
Once isolated service testing passes, a PR is raised from `dev` into `staging` (again requiring two-admin sign-off). On merge, it auto-deploys to UAT where integration tests validate end-to-end interactions across all 25 microservices.

#### 5. Master Branch (Production Release Window)
Once validated in UAT, a PR is raised from `staging` into `master`. Production releases are not continuous; they are scheduled on a designated production deployment window with manual promotion confirmation and automated canary health verification.
""")
                }
            ],
            "additional_questions": ADDITIONAL_PROJECT_QUESTIONS,
            "cluster_sizing_specs": {
                "microservices": 25,
                "target_cpu": 200,
                "instance_type": "m6i.4xlarge",
                "instance_vcpu": 16,
                "instance_ram_gb": 64,
                "allocatable_cpu_per_node": 14,
                "allocatable_ram_per_node": 58,
                "base_nodes_needed": 15,
                "redundancy_buffer_nodes": 3,
                "total_nodes": 18,
                "total_vcpu": 288,
                "total_ram_gb": 1152,
                "azs": 3,
                "nodes_per_az": 6
            }
        }

project_service = ProjectService()
