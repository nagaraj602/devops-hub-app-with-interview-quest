import re
import datetime
from typing import Optional

BASE_CATEGORIES_LIST = [
    "Behavioral", "Jenkins", "Git / GitHub", "General", "Terraform / IaC",
    "Docker", "AWS / Cloud", "Kubernetes", "Monitoring", "Linux",
    "Python", "Security", "Shell script", "Ansible", "System Design",
    "Networking", "CI/CD", "AI/ML"
]

CATEGORY_NORMALIZE_MAP = {
    "ci/cd": "CI/CD",
    "cicd": "CI/CD",
    "jenkins": "Jenkins",
    "docker": "Docker",
    "kubernetes": "Kubernetes",
    "k8s": "Kubernetes",
    "linux": "Linux",
    "shell script": "Shell script",
    "shell": "Shell script",
    "bash": "Shell script",
    "cloud": "AWS / Cloud",
    "aws": "AWS / Cloud",
    "iac": "Terraform / IaC",
    "terraform": "Terraform / IaC",
    "security": "Security",
    "networking": "Networking",
    "monitoring": "Monitoring",
    "system design": "System Design",
    "behavioral": "Behavioral",
    "git": "Git / GitHub",
    "github": "Git / GitHub",
    "ansible": "Ansible",
    "python": "Python",
    "boto3": "Python",
    "ai/ml": "AI/ML",
    "build tools": "Build Tools",
    "other": "General",
    "nagaraj's interview": "Nagaraj's Interview",
    "nagaraj interview": "Nagaraj's Interview"
}

def is_nagaraj_interview_file(filename: str) -> bool:
    """
    Checks if a markdown file represents Nagaraj's personal interviews.
    Matches *nagaraj*interview* or *my*interview* case-insensitively.
    """
    if not filename:
        return False
    fn = filename.lower()
    return bool(re.search(r'nagaraj.*interview', fn) or re.search(r'my.*interview', fn))

def parse_date_to_timestamp(date_str: str) -> float:
    """Parses various date formats into epoch timestamp for chronological sorting."""
    if not date_str:
        return 0.0
    cleaned = date_str.replace("*", "").strip()
    for fmt in [
        "%d-%m-%Y %I:%M %p", "%d-%m-%Y %H:%M", "%d-%m-%Y",
        "%d-%b-%Y %I:%M %p", "%d-%b-%Y", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"
    ]:
        try:
            return datetime.datetime.strptime(cleaned, fmt).timestamp()
        except ValueError:
            pass
    m = re.search(r'(\d{1,2})-(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)-(\d{4})', cleaned, re.IGNORECASE)
    if m:
        try:
            return datetime.datetime.strptime(f"{int(m.group(1)):02d}-{m.group(2).capitalize()}-{m.group(3)}", "%d-%b-%Y").timestamp()
        except Exception:
            pass
    return 0.0

def normalize_category(cat: str) -> str:
    if not cat:
        return "General"
    cleaned = cat.strip().lower()
    return CATEGORY_NORMALIZE_MAP.get(cleaned, cat.strip())

def detect_category_from_text(q_text: str, ans_text: str = "", section_cat: str = "") -> str:
    ql = q_text.lower().strip()
    tl = (q_text + " " + ans_text).lower()

    # Explicit Overrides:
    # 1. IP Blacklisting -> AWS / Cloud
    if "blacklisting of an ip" in ql or "blacklisting an ip" in ql or "blacklist of an ip" in ql or "blacklisting" in ql:
        return "AWS / Cloud"
        
    # 2. RBAC Item and Global roles -> Jenkins (Role-based Authorization Strategy plugin)
    if "item and global roles" in ql or "global roles in rbac" in ql or "item roles" in ql:
        return "Jenkins"
        
    # 3. Copy module and templates -> Ansible
    if "copy module and templates" in ql or ("copy module" in ql and "template" in ql) or "copy module" in ql:
        return "Ansible"
        
    # 4. Database SQL concepts -> System Design
    if (
        "primary key and a unique key" in ql or
        "primary key" in ql or
        "delete, drop, and truncate" in ql or
        "delete, drop and truncate" in ql or
        ("delete" in ql and "drop" in ql and "truncate" in ql) or
        "indexing in the context of databases" in ql or
        "which databases have you worked on" in ql
    ):
        return "System Design"

    # Behavioral
    if any(w in ql for w in [
        "introduce yourself", "tell me about yourself", "brief introduction", "walk me through your resume",
        "why change of company", "team size", "separate devops team", "onshore/offshore", "notice period",
        "salary expectation", "relocate", "conflict", "mistake", "hire you", "strengths", "weaknesses",
        "what is your project about", "explain your project", "about your current project", "roles and responsibilities",
        "day to day", "day-to-day", "working model", "why do you want to join", "rate your communication",
        "share your screen so we can go through"
    ]):
        return "Behavioral"

    # Dockerfile / Docker priority
    if any(w in ql for w in ["write a complete dockerfile", "write a dockerfile", "dockerfile that:"]):
        return "Docker"

    # Python
    if any(w in ql for w in [
        "python", "boto3", "equilibrium index", "list and tuple", "difference between list and tuple",
        "dictionary in python", "pip install", "pandas", "numpy", "python script", "python program",
        "python code", "python skills", "exceptions in python", "package dependencies in python",
        "read from a file in python"
    ]) or re.search(r'\bpython\b', ql):
        if not ("ocr application that needs to be deployed on aws" in ql or "deploying and managing this workload" in ql):
            return "Python"

    # Terraform / IaC
    if any(w in ql for w in ["terraform", "tfstate", "iac", "hcl", "state lock", "terragrunt", "remote backend", "terraform plan", "terraform apply", "terraform code", "one terraform code"]):
        return "Terraform / IaC"

    # Jenkins / Pipeline
    if any(w in ql for w in [
        "jenkins", "jenkinsfile", "jnlp", "blue ocean", "jenkins agent", "jenkins master", "jenkins controller",
        "shared library", "declarative", "scripted pipeline", "post-build actions", "pipeline", "pipelines",
        "ci/cd pipeline", "ci pipeline", "cd pipeline", "deployment pipeline", "build pipeline",
        "multibranch", "release pipeline"
    ]) or re.search(r'\bjenkins\b', ql) or re.search(r'\bpipeline\b', ql):
        return "Jenkins"

    # Kubernetes / Helm / ArgoCD
    if any(w in ql for w in [
        "k8s", "kubernetes", "pod", "pods", "ingress", "clusterip", "nodeport", "hpa", "helm",
        "daemonset", "statefulset", "kubelet", "kubectl", "etcd", "coredns", "configmap", "calico",
        "crashloopbackoff", "oomkilled", "karpenter", "argocd", "argo cd", "flux", "gitops"
    ]):
        return "Kubernetes"

    # Docker / Containers
    if any(w in ql for w in ["docker", "dockerfile", "container", "containers", "multistage", "multi-stage", "entrypoint", "docker-compose", "distroless", "image build", "ecr"]):
        return "Docker"

    # Ansible
    if any(w in ql for w in ["ansible", "playbook", "inventory", "ad-hoc", "awx", "tower"]):
        return "Ansible"

    # Git / GitHub
    if any(w in ql for w in ["github", "gitlab", "bitbucket", "rebase", "cherry-pick", "merge conflict", "branching", "pull request", "git commit", "git stash"]) or re.search(r'\bgit\b', ql):
        return "Git / GitHub"

    # Monitoring
    if any(w in ql for w in ["prometheus", "grafana", "monitoring", "datadog", "pagerduty", "alertmanager", "splunk", "elk", "logstash", "observability", "metrics", "cadvisor"]):
        return "Monitoring"

    # Security & Quality
    if any(w in ql for w in ["trivy", "sonarqube", "vulnerability", "owasp", "cve", "snyk", "vault", "kms", "code spells", "code smells", "linting"]):
        return "Security"

    # AWS / Cloud
    if any(w in ql for w in ["aws", "ec2", "s3", "vpc", "nacl", "security group", "route 53", "route53", "dynamodb", "cloudwatch", "cloudtrail", "iam", "eks", "fargate", "ecs", "alb", "nlb", "load balancer", "load balancers", "ebs", "rds", "lambda", "cloudfront", "transit gateway", "databricks", "azure", "gcp"]):
        return "AWS / Cloud"

    # Networking
    if any(w in ql for w in ["subnet", "cidr", "osi model", "tcp/ip", "dns", "dhcp", "reverse proxy"]):
        return "Networking"

    # System Design
    if any(w in ql for w in ["system design", "high availability", "disaster recovery", "microservices architecture"]):
        return "System Design"

    # Shell script
    if any(w in ql for w in ["bash script", "shell script", "shell scripting", "crontab", "question to check shell script"]):
        return "Shell script"

    # Linux
    if any(w in ql for w in ["linux", "grep", "awk", "sed", "systemd", "systemctl", "chmod", "chown", "iostat", "top", "htop", "free -m", "vmstat", "uptime"]):
        return "Linux"

    # CI/CD
    if any(w in ql for w in ["ci/cd", "continuous integration", "continuous deployment"]):
        return "Jenkins"

    # AI/ML
    if any(w in ql for w in ["ai/ml", "artificial intelligence", "machine learning", "llm", "genai", "copilot", "chatgpt"]):
        return "AI/ML"

    if section_cat and section_cat not in ["General", "Other"]:
        norm_s = normalize_category(section_cat)
        if norm_s != "General":
            return norm_s

    # Fallback to answer text keywords
    if any(w in tl for w in ["def ", "boto3", "python", "equilibrium index"]):
        return "Python"
    if any(w in tl for w in ["jenkins", "jenkinsfile", "pipeline"]):
        return "Jenkins"
    if any(w in tl for w in ["k8s", "kubernetes", "pod", "kubectl"]):
        return "Kubernetes"
    if any(w in tl for w in ["docker", "dockerfile", "container"]):
        return "Docker"
    if any(w in tl for w in ["terraform", "tfstate", "hcl"]):
        return "Terraform / IaC"
    if any(w in tl for w in ["aws", "ec2", "s3", "vpc"]):
        return "AWS / Cloud"
    if any(w in tl for w in ["ansible", "playbook"]):
        return "Ansible"
    if any(w in tl for w in ["git", "github", "rebase", "branch"]):
        return "Git / GitHub"
    if any(w in tl for w in ["prometheus", "grafana"]):
        return "Monitoring"
    if any(w in tl for w in ["trivy", "sonarqube", "vulnerability"]):
        return "Security"
    if any(w in tl for w in ["linux", "bash", "shell", "grep", "awk", "systemd"]):
        return "Linux"

    return "General"

def get_fallback_answer_for_question(q_text: str, c_name: str, r_name: str) -> str:
    ql = q_text.lower()
    if any(w in ql for w in ["introduce yourself", "brief introduction", "walk me through", "tell me about yourself"]):
        return (
            "I am a DevOps Engineer with 5 years of practical IT experience, primarily focusing on CI/CD automation, "
            "AWS cloud infrastructure, and containerized deployments with Docker and Kubernetes.\n\n"
            "### 1. Core Technical Skills\n"
            "- **CI/CD & Source Control:** Jenkins (Declarative Pipelines), Git/GitHub (branching strategies, merge conflict resolution), Maven build tool, SonarQube code quality gates.\n"
            "- **Cloud & Networking (AWS):** VPC (public and private subnets, Internet Gateway, NAT Gateway, Route Tables), EC2, Auto Scaling Groups, Application Load Balancer (ALB), S3, IAM, and CloudWatch.\n"
            "- **Containers & Orchestration:** Docker (writing Dockerfiles, multi-stage builds, image optimization), AWS ECR, and Kubernetes (Deployments, Services, ConfigMaps, Secrets, Ingress, and HPA).\n"
            "- **Infrastructure as Code (IaC) & Automation:** Terraform (modular code, remote S3 state backend with DynamoDB locking), Ansible playbooks, and Shell/Bash scripting for routine OS tasks.\n\n"
            "### 2. Day-to-Day Responsibilities\n"
            "- Managing and troubleshooting CI/CD build and deployment pipelines in Jenkins.\n"
            "- Provisioning and updating AWS infrastructure resources using Terraform modules.\n"
            "- Containerizing applications and managing Kubernetes workloads across DEV, QA, UAT, and PROD.\n"
            "- Resolving Jira tickets related to build failures, deployments, Git merges, and infrastructure monitoring."
        )
    if "role" in ql and ("responsibility" in ql or "responsibilities" in ql):
        return (
            "In my current role as a DevOps Engineer, my primary responsibilities include:\n\n"
            "1. **CI/CD Pipeline Management:** Creating and maintaining declarative Jenkins pipelines for our microservices, automating build, test, SonarQube scans, Docker packaging, and deployment.\n"
            "2. **Cloud Infrastructure (IaC):** Writing and maintaining Terraform configurations to provision AWS resources like VPCs, subnets, EC2 instances, and security groups with S3 and DynamoDB remote state locking.\n"
            "3. **Containerization & Deployment:** Building Docker images using multi-stage builds, pushing to Amazon ECR, and deploying applications onto Kubernetes clusters.\n"
            "4. **Configuration & Scripting:** Writing Bash scripts and Ansible playbooks for system configuration, log rotation, and server maintenance.\n"
            "5. **Production Support & Troubleshooting:** Monitoring application and infrastructure health using CloudWatch, debugging deployment failures, and working closely with development and QA teams."
        )
    return (
        f"In {c_name} ({r_name}), the interviewer is looking for practical hands-on understanding. "
        "In production, I ensure reliability by following infrastructure best practices, verifying changes in DEV/QA before PROD, "
        "and automating repetitive tasks through CI/CD and scripts."
    )
