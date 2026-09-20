import os
import re
from pathlib import Path
from typing import Dict, Any, List, Optional
from app.config import PROJECT_FILE
from app.services.project_data import (
    PROJECT_METRICS,
    CRUCIAL_INTERVIEW_QUESTIONS,
    CLUSTER_SIZING_SPECS
)

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

class ProjectService:
    def __init__(self, project_path: Optional[str] = None):
        self.project_path = Path(project_path or PROJECT_FILE)

    def get_project_data(self) -> Dict[str, Any]:
        """Loads and parses the Project documentation with clean modular sections."""
        content = ""
        if self.project_path.exists():
            with open(self.project_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()

        # Render HTML for all crucial deep-dive questions
        deep_dives = []
        for q in CRUCIAL_INTERVIEW_QUESTIONS:
            q_copy = dict(q)
            q_copy["detailed_answer_html"] = render_md(q["detailed_answer"].strip())
            deep_dives.append(q_copy)

        return {
            "title": "E-Commerce - Marketplace Risk Detection Platform",
            "guide_badge": "Project Architecture & Guide",
            "overview_paragraphs": [
                "The project involved building a Marketplace Seller Risk & Abuse Detection Platform for a large online marketplace connecting third-party sellers with buyers. As the platform scaled to tens of thousands of sellers and millions of listings, it became a target for fake listings, review manipulation, seller account takeovers, and abuse ratings using networks of fake accounts.",
                "The platform continuously ingests signals from listing creation, seller account activity, orders, and reviews, detects suspicious patterns in near real-time, routes high-confidence cases for automated action and lower-confidence cases to a trust & safety analyst queue, and triggers enforcement actions (seller suspension, listing takedown, payout holds) through the marketplace's existing systems.",
                "It was designed using a microservices architecture to allow independent scaling of ingestion, detection, and case-management workloads."
            ],
            "microservices": [
                {"name": "Listing Ingestion Service", "role": "Ingestion", "lang": "Go", "detail": "Consumes new listing events, validates payload schemas, and pushes to Kafka topics."},
                {"name": "Review Stream Normalizer", "role": "Ingestion", "lang": "Go", "detail": "Normalizes review and rating streams across multiple regional storefronts."},
                {"name": "Velocity Check Service", "role": "Detection", "lang": "Java / Spring Boot", "detail": "Stateful sliding-window counters in Redis (e.g. 100 listings in 5 minutes)."},
                {"name": "Anomaly Scoring Engine", "role": "Detection", "lang": "Python / FastAPI", "detail": "Runs ML inference models (XGBoost) for synthetic pattern detection."},
                {"name": "Graph Analysis Service", "role": "Detection", "lang": "Go / Neo4j", "detail": "Maintains seller-device-bank account linkage graphs to uncover fraud rings."},
                {"name": "Case Management API", "role": "Case Management", "lang": "Java / Spring Boot", "detail": "Manages review queues, SLA assignments, and manual analyst overrides."},
                {"name": "Enforcement Orchestration", "role": "Enforcement", "lang": "Go", "detail": "Fires webhooks to suspend accounts, take down listings, or hold payouts."}
            ],
            "tools_and_tech": [
                "AWS (EKS, MSK, ElastiCache, S3, RDS, WAF)",
                "Docker & Kubernetes (Helm, HPA, KEDA)",
                "Jenkins (Shared Libraries, SonarQube, Trivy)",
                "Terraform & Ansible",
                "Prometheus, Grafana & ELK Stack"
            ],
            "key_results": [
                "Reduced malicious listing detection latency from multiple days to under 10 minutes.",
                "Automated 60% of enforcement actions with strict auditability, freeing analysts for complex fraud rings.",
                "Handled 5x event volume spikes during major promotional sales events with zero pipeline lag."
            ],
            "anticipated_follow_ups": [
                {
                    "question": "How did you prevent the detection pipeline from falling behind during sales events?",
                    "answer": "We scaled consumer pods horizontally using KEDA based on Kafka topic consumer lag rather than CPU alone, partitioned topics by seller ID for parallel processing, and implemented an in-memory Redis sliding window to keep stateful checks O(1)."
                },
                {
                    "question": "How did you handle false positives in automated enforcement?",
                    "answer": "Rule changes went through Jenkins pipelines that ran them against shadow traffic first, comparing flag rates against production before promoting, with automated rollback if false-positive rate SLOs were breached."
                },
                {
                    "question": "How did the platform avoid becoming a single point of failure for enforcement actions?",
                    "answer": "The Enforcement Orchestration Service only made outbound calls to existing seller/listing APIs. If those were unavailable, we queued actions with retry/backoff rather than blocking the detection pipeline."
                }
            ],
            "preparation_checklist": [
                {
                    "id": "prep_intro",
                    "number": 1,
                    "title": "1. Introduction",
                    "subtitle": "Tell me about yourself / Walk me through your profile",
                    "content_html": render_md("""
*Use this response when the interviewer asks:*
• *Tell me about yourself / your background*
• *Walk me through your resume or profile*
• *What are your day-to-day responsibilities?*

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
The CI pipeline runs on every PR into dev, staging, or master, acting as our pre-merge quality gate. It starts with a Git checkout, followed by unit tests and static code analysis using SonarQube with a quality gate that hard-fails on code quality issues. Once Sonar passes, we build the Docker image locally without pushing it to ECR, then run **Trivy** scans across the filesystem, Dockerfile configuration, and the built image, gating on Critical and High severity vulnerabilities. If any check fails, the developer fixes the code on their feature branch and re-raises the PR.

#### CD Pipeline (Deployment Pipeline)
The CD pipeline runs after a PR is approved and merged, handling build and deployment. It builds the Docker image, pushes it to Amazon ECR, updates our Helm chart values, and deploys to the environment corresponding to the branch.
* **On merge to `dev`:** Auto-deployed to DEV for isolated QA testing.
* **On merge to `staging`:** Auto-deployed to UAT for end-to-end integration testing.
* **On merge to `master`:** Pauses at a manual confirmation approval step, releasing to production in scheduled maintenance windows.
""")
                },
                {
                    "id": "prep_branching",
                    "number": 4,
                    "title": "4. Explain your Branching Strategy",
                    "subtitle": "What branching strategy do you use for version control and why?",
                    "content_html": render_md("""
We follow a robust branching strategy with **`dev`**, **`staging`**, and **`master`** as our primary long-lived branches, with all feature work happening in short-lived feature branches created off `dev`.

1. **Feature Development:** Developers branch off `dev` (`feature/JIRA-101`), develop and test locally, then open a PR back to `dev`.
2. **Pre-Merge Quality Gate:** PRs trigger automated SonarQube and Trivy scans. In addition, PRs require **two-admin approval** before merge.
3. **Promotion Flow:** Changes flow sequentially from `dev` (DEV environment) -> `staging` (UAT integration) -> `master` (Production).
""")
                }
            ],
            "metrics": PROJECT_METRICS,
            "additional_questions": deep_dives,
            "cluster_sizing_specs": CLUSTER_SIZING_SPECS
        }

project_service = ProjectService()
