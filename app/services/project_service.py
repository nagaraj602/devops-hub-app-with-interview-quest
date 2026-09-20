import os
from pathlib import Path
from typing import Dict, Any, List, Optional
from app.config import PROJECT_FILE

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
"""
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
"""
    }
]

class ProjectService:
    def __init__(self, project_path: Optional[str] = None):
        self.project_file = Path(project_path or PROJECT_FILE)

    def get_project_data(self) -> Dict[str, Any]:
        raw_content = ""
        if self.project_file.exists():
            try:
                with open(self.project_file, "r", encoding="utf-8", errors="ignore") as f:
                    raw_content = f.read()
            except Exception as e:
                raw_content = f"Error reading project file: {e}"

        # Parse sections from Project file
        sections = self._parse_sections(raw_content)

        return {
            "title": "E-Commerce Marketplace Seller Risk & Abuse Detection Platform",
            "raw_content": raw_content,
            "sections": sections,
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

    def _parse_sections(self, content: str) -> List[Dict[str, str]]:
        sections = []
        current_title = "Overview"
        current_lines = []

        for line in content.splitlines():
            trimmed = line.strip()
            # Check major headings
            if trimmed in [
                "Project Overview", "Microservices Architecture", "Tools & Technologies",
                "Key Results & Impact", "Anticipated Follow-Up Questions", "Preparation Questions & Answers",
                "Day-to-Day Responsibilities", "Can you walk me through the key components and architecture of your project?",
                "How do you handle continuous integration and continuous deployment?",
                "What branching strategy do you use for version control and why?"
            ]:
                if current_lines:
                    sections.append({
                        "title": current_title,
                        "content": "\n".join(current_lines).strip()
                    })
                    current_lines = []
                current_title = trimmed
            else:
                current_lines.append(line)

        if current_lines:
            sections.append({
                "title": current_title,
                "content": "\n".join(current_lines).strip()
            })

        return sections

project_service = ProjectService()
