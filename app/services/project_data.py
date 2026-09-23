# ==============================================================================
# DevOps Hub - Project Architecture Data & Crucial Deep-Dive Q&As
# ==============================================================================

# High-impact production KPI cards
PROJECT_METRICS = [
    {
        "value": "< 10 Mins",
        "label": "Detection Latency",
        "detail": "Down from multiple days of manual batch reviews",
        "icon": "fa-bolt",
        "color": "var(--primary)"
    },
    {
        "value": "60% Reduction",
        "label": "Manual Review Workload",
        "detail": "Automated actioning on high-confidence risk signals",
        "icon": "fa-shield-halved",
        "color": "#10b981"
    },
    {
        "value": "25 Microservices",
        "label": "Decoupled Architecture",
        "detail": "Decoupled Ingestion, Detection & Enforcement pipelines",
        "icon": "fa-cubes",
        "color": "#f59e0b"
    },
    {
        "value": "18 Worker Nodes",
        "label": "Multi-AZ EKS Cluster",
        "detail": "288 vCPUs, 1,152 GB RAM with N+1 AZ resilience",
        "icon": "fa-server",
        "color": "#8b5cf6"
    }
]

# Crucial Architectural Interview Deep-Dives
CRUCIAL_INTERVIEW_QUESTIONS = [
    {
        "id": "proj_q_team_structure",
        "question": "How many DevOps teams, developers, QA, and testers were there on the project?",
        "executive_summary": "1 Dedicated Platform/DevOps Team (4 Engineers), ~30 Developers across 5 domain squads, and 6 QA Engineers (4 SDETs + 2 Functional testers), totaling ~42 engineering members.",
        "detailed_answer": """
### 👥 Engineering & DevOps Team Structure

Our organization followed a cross-functional squad model supported by a centralized DevOps Platform team:

#### 1. DevOps & Platform Engineering Team (1 Centralized Team — 4 Engineers)
* **1 Lead Cloud Architect:** Owned AWS cloud architecture, EKS cluster topology, VPC networking, IAM security policies, and Terraform modules.
* **2 Senior DevOps Engineers:** Maintained CI/CD pipelines (Jenkins Shared Libraries & Helm), Docker security scanning (Trivy), Prometheus/Grafana monitoring, and Kubernetes autoscaling (HPA/KEDA).
* **1 Associate DevOps Engineer:** Handled Jira developer tickets, environment provisioning, Vault/AWS Secrets Manager access, and build triage.

#### 2. Development Squads (~30 Software Engineers across 5 Squads)
Each squad had 5–7 developers (primarily Go and Java/Spring Boot) with an embedded Tech Lead:
* **Squad 1 — Ingestion & Streaming (5 Devs):** Kafka event streaming, schema validation, and listing/order event deduplication.
* **Squad 2 — Velocity Rule Engine (6 Devs):** Low-latency risk rule evaluation using Redis in-memory sliding counters.
* **Squad 3 — Anomaly Scoring & Graph ML (6 Devs):** Machine learning inference APIs and Neo4j buyer-seller link analysis.
* **Squad 4 — Analyst Case Portal (7 Devs):** Workflow management engine, React console, and SLA review queues.
* **Squad 5 — Enforcement Actions (6 Devs):** Webhooks and transactional dispatchers calling marketplace APIs for seller bans and payout holds.

#### 3. Quality Assurance & Testing Team (6 QA Engineers)
* **4 SDETs (Automation Engineers):** Contract testing (Pact), end-to-end API suites (REST Assured/PyTest), and load testing (k6/JMeter) integrated into Jenkins PR checks.
* **2 Manual & Risk Exploratory Testers:** Simulated fraud patterns, coordinated ring abuses, and validated manual analyst override workflows.
"""
    },
    {
        "id": "proj_q_cluster_sizing",
        "question": "How many nodes were there in the cluster for these 25 microservices?",
        "executive_summary": "18 Worker Nodes of type m6i.4xlarge (16 vCPUs, 64 GB RAM each) spread across 3 Availability Zones (6 nodes per AZ), giving 288 total vCPUs and 1,152 GB RAM with safe buffer.",
        "detailed_answer": """
### 🖥️ Simple, Step-by-Step Cluster Sizing Calculation

Here is the straightforward math used to decide the number of worker nodes:

#### Step 1: Workload Needs
* **25 microservices** run in our cluster.
* Total CPU required by all microservices combined: **200 vCPUs**.
* Memory needed: Java and Go services average **3.5 GB of RAM per vCPU** = **~700 GB RAM total**.

#### Step 2: Choosing the EC2 Instance Type
* We chose **m6i.4xlarge** worker nodes.
* Each node has: **16 vCPUs** and **64 GB RAM**.

#### Step 3: Reserving Resources for Kubernetes System
* Every node runs the OS, Kubelet, AWS networking (aws-node), and monitoring agents (Prometheus, Fluentbit).
* This system overhead takes roughly **2 vCPUs** and **6 GB RAM** per node.
* **Usable space left per node for microservices:** **14 vCPUs** and **58 GB RAM**.

#### Step 4: How Many Nodes Are Needed for 200 vCPUs?
* Divide total CPU by usable CPU per node:
  $$\\text{Nodes needed} = \\frac{200 \\text{ vCPUs}}{14 \\text{ vCPUs/node}} = 14.3 \\approx \\mathbf{15 \\text{ nodes}}$$
* Memory check: $15 \\text{ nodes} \\times 58 \\text{ GB} = 870 \\text{ GB RAM}$ (comfortably covers the 700 GB needed).

#### Step 5: High Availability Across 3 Availability Zones
* We deploy across **3 AWS Availability Zones** (AZ A, AZ B, AZ C).
* 15 nodes divided across 3 AZs = **5 nodes per AZ**.

#### Step 6: Adding Safety Buffer (N+1 per Zone)
* If an entire node crashes or is drained for upgrades, we need spare capacity so pods aren't stuck waiting.
* We add **1 spare node per AZ** (6 nodes per AZ).
* **Final Node Count:** **6 nodes/AZ × 3 AZs = 18 Nodes Total**.

#### Summary Table
| Metric | Per Node (m6i.4xlarge) | Entire Cluster (18 Nodes) |
| :--- | :--- | :--- |
| **Total vCPUs** | 16 vCPUs | **288 vCPUs** (~30% headroom for sales spikes) |
| **Total RAM** | 64 GB RAM | **1,152 GB (1.15 TB) RAM** |
| **Zone Distribution** | Balanced | **6 Nodes in AZ-A, 6 in AZ-B, 6 in AZ-C** |
| **Fault Tolerance** | N+1 per AZ | Zero downtime even if a node in every zone fails |
"""
    },
    {
        "id": "proj_q_cicd_release",
        "question": "How do you handle CI/CD zero-downtime releases and rollback strategy across 25 microservices?",
        "executive_summary": "We use Jenkins Shared Libraries with Helm and ArgoCD for GitOps rolling deployments with readines probes, automated health verification, and instant rollback upon SLA breach.",
        "detailed_answer": """
### 🚀 Zero-Downtime Deployment & Rollback Architecture

#### 1. Deployment Strategy: Rolling Update with Anti-Affinity
* Every microservice has at least **2 to 4 pod replicas** configured with `podAntiAffinity` so pods are scheduled on separate nodes across different Availability Zones.
* In the Kubernetes Deployment manifest, we configure:
  ```yaml
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: 25%        # Spawns new version pods first before taking down old ones
      maxUnavailable: 0    # Ensures 100% of required replicas remain active throughout
  ```
* **Readiness & Liveness Probes:** Kubernetes routes live traffic only after the container passes health checks (`/actuator/health` or `/healthz`) for 15 consecutive seconds.

#### 2. Automated Canary Validation & Instant Rollbacks
* **Shadow / Canary Verification:** Jenkins runs new pipeline releases against a canary subset (5% traffic) and monitors error rates via Prometheus.
* **Instant Rollback Trigger:** If P99 latency exceeds 200ms or 5xx error rate spikes above 0.5% during deployment, ArgoCD / Helm initiates an automatic rollback (`helm rollback <release> <revision>`) in under 30 seconds.
"""
    },
    {
        "id": "proj_q_kafka_scaling",
        "question": "How do you manage Kafka consumer lag, backpressure, and autoscaling under sudden flash sale traffic surges?",
        "executive_summary": "We use KEDA (Kubernetes Event-driven Autoscaling) tied to Prometheus Kafka consumer lag metrics to autoscale consumer microservices horizontally before queues overflow.",
        "detailed_answer": """
### ⚡ Kafka Consumer Lag & Autoscaling Strategy

#### 1. Autoscaling with KEDA
* Traditional CPU-based HPA is often too slow to react to message spikes because consumer pods might stay at 40% CPU while thousands of unread messages accumulate in Kafka topics.
* We installed **KEDA (Kubernetes Event-driven Autoscaling)** and configured a `ScaledObject` that queries Kafka lag:
  ```yaml
  apiVersion: keda.sh/v1alpha1
  kind: ScaledObject
  metadata:
    name: kafka-order-consumer-scaler
  spec:
    scaleTargetRef:
      name: order-ingestion-service
    minReplicaCount: 4
    maxReplicaCount: 24
    triggers:
    - type: kafka
      metadata:
        bootstrapServers: kafka-cluster.prod:9092
        consumerGroup: risk-detection-group
        topic: marketplace-orders
        lagThreshold: "150"  # Scales out 1 additional pod for every 150 lagging messages
  ```

#### 2. Backpressure & Partition Management
* The Kafka topic has **32 partitions**, allowing consumer pods to scale horizontally up to 32 parallel active consumers.
* Consumer microservices implement exponential backoff retries with Dead Letter Queues (DLQ) for malformed events, preventing poisoning of the main processing stream.
"""
    },
    {
        "id": "proj_q_secrets_security",
        "question": "How do you secure inter-service communication and manage database/API secrets in Kubernetes?",
        "executive_summary": "We enforce mutual TLS via Istio Service Mesh, manage fine-grained pod IAM permissions using IRSA (IAM Roles for Service Accounts), and sync secrets dynamically using External Secrets Operator with AWS Secrets Manager.",
        "detailed_answer": """
### 🔐 Security Boundaries & Secrets Management

#### 1. Dynamic Secret Injection
* We **never commit secrets to Git** or store static base64 secrets in Kubernetes manifests.
* We use **External Secrets Operator (ESO)** connected to AWS Secrets Manager. Secrets (DB passwords, Redis auth, third-party API tokens) are automatically synchronized into Kubernetes Secrets and rotated automatically every 30 days without pod restarts.

#### 2. Least Privilege with AWS IRSA
* Microservices authenticate to AWS resources (S3 buckets, DynamoDB, SQS) using **IAM Roles for Service Accounts (IRSA)**.
* EKS projects an OIDC token into the pod container, completely eliminating long-lived AWS Access Keys and Secret Keys.

#### 3. Network Isolation
* Default deny-all Kubernetes NetworkPolicies prevent cross-namespace unauthorized traffic.
* Istio Service Mesh enforces strict **mTLS (Mutual TLS)** encryption for all pod-to-pod communication inside the VPC.
"""
    },
    {
        "id": "proj_q_cluster_upgrade",
        "question": "How do you perform a zero-downtime cluster upgrade in Kubernetes (Amazon EKS)?",
        "executive_summary": "We execute semi-annual zero-downtime upgrades (most recently Kubernetes 1.36.4 to 1.37) using modern Terraform >= 1.10, Velero S3 backups with EBS CSI volume snapshots, PodDisruptionBudgets (PDB), and Blue/Green Managed Node Groups with PDB-guarded draining.",
        "detailed_answer": """
### 🔄 Zero-Downtime EKS Cluster Upgrade (Kubernetes 1.36.4 → 1.37)

In enterprise production, we maintain a proactive upgrade cadence: **we upgrade our Kubernetes clusters twice a year** (roughly every 5 to 6 months) across our **AWS EKS** multi-cluster fleet provisioned via modern **Terraform (>= 1.10.0)**.

---

#### Why We Upgrade Twice a Year (Strategic & Technical Rationale)
1. **Kubernetes Upstream Support Lifecycle (N-2 Window):** The community supports only the 3 most recent minor versions (~14 months). Upgrading biannually keeps us strictly within official support windows.
2. **AWS EKS Extended Support Surcharges (Cost Governance):** AWS charges **$0.60/hour per cluster** under extended support compared to **$0.10/hour** for standard support—a **600% price increase** that costs hundreds of extra dollars monthly per cluster.
3. **Preventing Technical Debt & Version Skew Deadlock:** Kubernetes components cannot skip minor versions. Falling behind accumulates immense debt and forces risky multi-step sequential upgrades.
4. **Security Vulnerability (CVE) & Runtime Patching:** New minor/patch releases remediate critical CVEs across the API server, kubelet, and `containerd`/`runc` runtimes.
5. **Ecosystem & Add-on Compatibility:** Modern Ingress controllers, Helm charts, and CSI/CNI drivers deprecate older API versions.

---

#### End-to-End Zero-Downtime Upgrade Architecture
```
+---------------------------------------------------------------------------------------------------------+
| PHASE 1: PRE-CHECKS & AUDIT      PHASE 2: COMPREHENSIVE BACKUP       PHASE 3: PDB VALIDATION            |
| - API Deprecations (kubent)     - Velero S3 Backup (CRDs, Secrets)  - MinAvailable / MaxUnavailable     |
| - Target 1.37 Release Notes     - EBS CSI Volume Snapshots          - Deadlock / Single-replica check   |
| - Subnet IP Capacity Audit      - EKS Config Export & RDS Snapshot  - PodAntiAffinity verification      |
+---------------------------------------------------------------------------------------------------------+
                                                     |
                                                     v
+---------------------------------------------------------------------------------------------------------+
| PHASE 4: CONTROL PLANE UPGRADE (Terraform 1.10)   | PHASE 5: CORE ADD-ONS SEQUENTIAL UPGRADE            |
| - cluster_version = "1.37"                        | 1. AWS VPC CNI (aws-node)                           |
| - Multi-AZ API Server Rolling Upgrade (AWS)       | 2. Kube-Proxy                                       |
| - Zero API downtime                               | 3. CoreDNS  4. AWS EBS CSI Driver                   |
+---------------------------------------------------------------------------------------------------------+
                                                     |
                                                     v
+---------------------------------------------------------------------------------------------------------+
| PHASE 6: ZERO-DOWNTIME WORKER NODE UPGRADE (BLUE/GREEN STRATEGY VIA TERRAFORM)                          |
| 1. Provision Green Node Group (v1.37)  --> Wait for Nodes Ready                                        |
| 2. Cordon Blue Nodes (v1.36)          --> Prevent new scheduling on old nodes                          |
| 3. Drain Blue Nodes Gracefully        --> PDB enforces gradual pod eviction to Green nodes             |
| 4. Health Check & Synthetic Smoke     --> Validate Ingress, Metrics, Pod Health                        |
| 5. Destroy Blue Node Group via IaC    --> Clean EC2 termination with zero dropped requests             |
+---------------------------------------------------------------------------------------------------------+
```

---

#### Step 1: Pre-Upgrade Planning & API Deprecation Audit
* **Audit Deprecated APIs:** Scan live cluster resources with `kubent -t 1.37.0` and Helm releases with `pluto detect-helm -t k8s=v1.37.0`.
* **Subnet IP Capacity Check:** Ensure private subnets have enough unallocated secondary IPs for the parallel Green node group to join the AWS VPC CNI:
  ```bash
  aws ec2 describe-subnets --filters "Name=tag:kubernetes.io/role/internal-elb,Values=1" \\
    --query "Subnets[*].[SubnetId,AvailableIpAddressCount,CidrBlock]" --output table
  ```

---

#### Step 2: Comprehensive Multi-Tier Disaster Recovery Backup (EKS-Focused)
> **AWS-Managed Control Plane Note:** In Amazon EKS, AWS automatically manages and replicates the control plane and etcd quorum across 3 Availability Zones under a 99.95% SLA. Backups focus on declarative state, application resources, and EBS persistent volumes:

1. **Velero Backup (Manifests, CRDs, Secrets & Persistent Volumes):**
   ```bash
   velero backup create k8s-136-to-137-preupgrade-$(date +%Y%m%d-%H%M) \\
     --include-namespaces='*' \\
     --snapshot-volumes=true \\
     --default-volumes-to-fs-backup=false \\
     --csi-snapshot-timeout=25m \\
     --wait
   ```
2. **Export Active EKS Cluster Configuration via AWS CLI:**
   ```bash
   aws eks describe-cluster --name prod-core-cluster --query "cluster" --output json > /var/backups/eks-cluster-config-1.36.4.json
   aws eks list-addons --cluster-name prod-core-cluster --output json > /var/backups/eks-addons-1.36.4.json
   ```
3. **Database Snapshot & Git Lock:**
   Trigger an AWS RDS/Aurora snapshot and tag the Terraform / GitOps repository (`git tag -a release-k8s-1.36.4`).

---

#### Step 3: Pod Disruption Budgets (PDB) & Resiliency Setup
Every production microservice must have a `PodDisruptionBudget` (`policy/v1`) with at least 2 replicas:
```yaml
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: order-service-pdb
  namespace: production
spec:
  minAvailable: 2  # Guarantees at least 2 healthy pods remain serving traffic during node drains
  selector:
    matchLabels:
      app: order-service
```
* **Anti-Pattern Warning:** Never configure `minAvailable: 1` or `100%` on a deployment with `replicas: 1`—it causes `kubectl drain` to deadlock.
* **Readiness Probes:** Mandatory so the eviction API only terminates the next pod after replacement pods pass health checks.

---

#### Step 4: Upgrading EKS Control Plane via Terraform 1.10+
```hcl
terraform {
  required_version = ">= 1.10.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.80"
    }
  }
}

module "eks" {
  source          = "terraform-aws-modules/eks/aws"
  version         = "~> 20.31"
  cluster_name    = "prod-core-cluster"
  cluster_version = "1.37"   # Upgraded from 1.36
  # ...
}
```
Apply the Terraform execution plan. AWS executes a zero-downtime rolling update across all 3 AZ API servers.

---

#### Step 5: Sequentially Upgrading Core Add-ons
Upgrade add-ons in exact order:
1. **Amazon VPC CNI (`aws-node`)** -> 2. **Kube-Proxy** -> 3. **CoreDNS** -> 4. **AWS EBS CSI Driver**.

---

#### Step 6: Zero-Downtime Worker Node Upgrade (Blue/Green Strategy)
1. **Define Green Node Group in Terraform:** Add `green_v137` alongside `blue_v136` and apply with target:
   ```bash
   terraform apply -target='module.eks.eks_managed_node_groups["green_v137"]'
   ```
2. **Cordon Blue Nodes:** Mark old nodes unschedulable:
   ```bash
   kubectl cordon -l eks.amazonaws.com/nodegroup=ng-app-v136
   ```
3. **Drain Blue Nodes Gracefully:**
   ```bash
   kubectl drain -l eks.amazonaws.com/nodegroup=ng-app-v136 \\
     --ignore-daemonsets \\
     --delete-emptydir-data \\
     --grace-period=60 \\
     --timeout=15m
   ```
   *Evicted pods dynamically reschedule onto ready Green 1.37 nodes under PDB protection without dropping traffic.*
4. **Decommission Blue Nodes:** Remove `blue_v136` from Terraform and run `terraform apply`.

---

#### Step 7: Post-Upgrade Validation & Disaster Recovery Matrix
* Verify cluster health: `kubectl get nodes -o wide` and check pod phases across namespaces.
* Execute synthetic HTTP smoke tests against Ingress ALBs and monitor latency in Datadog/Prometheus.

| Failure Stage | Blast Radius | Recovery & Rollback Procedure |
| :--- | :--- | :--- |
| **Pre-upgrade Backup Failure** | None | Abort upgrade. Investigate Velero S3 bucket permissions (IRSA) or EBS CSI snapshot volume connectivity before proceeding. |
| **Control Plane Stalled** | Control plane only | EKS control plane rollouts are transactional. AWS does not permit downgrading control plane versions; keep control plane at target version and engage AWS support. Worker nodes and pods remain operational. |
| **Green Node Group Join Failure** | Zero application impact | Uncordon Blue nodes (`kubectl uncordon`). Blue nodes continue serving live traffic while investigating Green node launch templates or subnet IP exhaustion. |
| **Application Crash on v1.37** | Isolated service | Revert application Deployment via Argo CD / Helm rollback. If manifest state is corrupted, restore the namespace from the **Velero backup** (`velero restore create --from-backup ...`). |
"""
    }
]

# Cluster Sizing Specification Constants
CLUSTER_SIZING_SPECS = {
    "recommended_instance": "m6i.4xlarge",
    "instance_vcpu": 16,
    "instance_ram_gb": 64,
    "system_overhead_vcpu": 2,
    "system_overhead_ram_gb": 6,
    "usable_vcpu": 14,
    "usable_ram_gb": 58,
    "workload_vcpu": 200,
    "workload_ram_gb": 700,
    "zones_count": 3,
    "nodes_per_zone": 6,
    "total_nodes": 18,
    "provisioned_vcpu": 288,
    "provisioned_ram_gb": 1152,
    "headroom_pct": 31
}
