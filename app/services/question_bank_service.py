import os
import re
import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional
from app.config import INTERVIEW_QUESTIONS_DIR

CATEGORIES_LIST = [
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
    "other": "General"
}

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

    # 1. Behavioral
    if any(w in ql for w in [
        "introduce yourself", "tell me about yourself", "brief introduction", "walk me through your resume",
        "why change of company", "team size", "separate devops team", "onshore/offshore", "notice period",
        "salary expectation", "relocate", "conflict", "mistake", "hire you", "strengths", "weaknesses",
        "what is your project about", "explain your project", "about your current project", "roles and responsibilities",
        "day to day", "day-to-day", "working model", "why do you want to join", "rate your communication",
        "share your screen so we can go through"
    ]):
        return "Behavioral"

    # 2. Dockerfile / Docker priority when explicitly asked to write Dockerfile or containerize
    if any(w in ql for w in ["write a complete dockerfile", "write a dockerfile", "dockerfile that:"]):
        return "Docker"

    # 3. Python
    if any(w in ql for w in [
        "python", "boto3", "equilibrium index", "list and tuple", "difference between list and tuple",
        "dictionary in python", "pip install", "pandas", "numpy", "python script", "python program",
        "python code", "python skills", "exceptions in python", "package dependencies in python",
        "read from a file in python"
    ]) or re.search(r'\bpython\b', ql):
        if not ("ocr application that needs to be deployed on aws" in ql or "deploying and managing this workload" in ql):
            return "Python"

    # 4. Terraform / IaC
    if any(w in ql for w in ["terraform", "tfstate", "iac", "hcl", "state lock", "terragrunt", "remote backend", "terraform plan", "terraform apply", "terraform code", "one terraform code"]):
        return "Terraform / IaC"

    # 5. Jenkins / Pipeline
    if any(w in ql for w in [
        "jenkins", "jenkinsfile", "jnlp", "blue ocean", "jenkins agent", "jenkins master", "jenkins controller",
        "shared library", "declarative", "scripted pipeline", "post-build actions", "pipeline", "pipelines",
        "ci/cd pipeline", "ci pipeline", "cd pipeline", "deployment pipeline", "build pipeline",
        "multibranch", "release pipeline"
    ]) or re.search(r'\bjenkins\b', ql) or re.search(r'\bpipeline\b', ql):
        return "Jenkins"

    # 6. Kubernetes / Helm / ArgoCD
    if any(w in ql for w in [
        "k8s", "kubernetes", "pod", "pods", "ingress", "clusterip", "nodeport", "hpa", "helm",
        "daemonset", "statefulset", "kubelet", "kubectl", "etcd", "coredns", "configmap", "calico",
        "crashloopbackoff", "oomkilled", "karpenter", "argocd", "argo cd", "flux", "gitops"
    ]):
        return "Kubernetes"

    # 7. Docker / Containers
    if any(w in ql for w in ["docker", "dockerfile", "container", "containers", "multistage", "multi-stage", "entrypoint", "docker-compose", "distroless", "image build", "ecr"]):
        return "Docker"

    # 8. Ansible
    if any(w in ql for w in ["ansible", "playbook", "inventory", "ad-hoc", "awx", "tower"]):
        return "Ansible"

    # 9. Git / GitHub
    if any(w in ql for w in ["github", "gitlab", "bitbucket", "rebase", "cherry-pick", "merge conflict", "branching", "pull request", "git commit", "git stash"]) or re.search(r'\bgit\b', ql):
        return "Git / GitHub"

    # 10. Monitoring
    if any(w in ql for w in ["prometheus", "grafana", "monitoring", "datadog", "pagerduty", "alertmanager", "splunk", "elk", "logstash", "observability", "metrics", "cadvisor"]):
        return "Monitoring"

    # 11. Security & Quality
    if any(w in ql for w in ["trivy", "sonarqube", "vulnerability", "owasp", "cve", "snyk", "vault", "kms", "code spells", "code smells", "linting"]):
        return "Security"

    # 12. AWS / Cloud
    if any(w in ql for w in ["aws", "ec2", "s3", "vpc", "nacl", "security group", "route 53", "route53", "dynamodb", "cloudwatch", "cloudtrail", "iam", "eks", "fargate", "ecs", "alb", "nlb", "load balancer", "load balancers", "ebs", "rds", "lambda", "cloudfront", "transit gateway", "databricks", "azure", "gcp"]):
        return "AWS / Cloud"

    # 13. Networking
    if any(w in ql for w in ["subnet", "cidr", "osi model", "tcp/ip", "dns", "dhcp", "reverse proxy"]):
        return "Networking"

    # 14. System Design
    if any(w in ql for w in ["system design", "high availability", "disaster recovery", "microservices architecture"]):
        return "System Design"

    # 15. Shell script
    if any(w in ql for w in ["bash script", "shell script", "shell scripting", "crontab", "question to check shell script"]):
        return "Shell script"

    # 16. Linux
    if any(w in ql for w in ["linux", "grep", "awk", "sed", "systemd", "systemctl", "chmod", "chown", "iostat", "top", "htop", "free -m", "vmstat", "uptime"]):
        return "Linux"

    # 17. CI/CD
    if any(w in ql for w in ["ci/cd", "continuous integration", "continuous deployment"]):
        return "Jenkins"

    # 18. AI/ML
    if any(w in ql for w in ["ai/ml", "artificial intelligence", "machine learning", "llm", "genai", "copilot", "chatgpt"]):
        return "AI/ML"

    if section_cat and section_cat not in ["General", "Other"]:
        norm_s = normalize_category(section_cat)
        if norm_s != "General":
            return norm_s

    # Answer text fallback
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

class QuestionBankService:
    def __init__(self, questions_dir: Optional[str] = None):
        self.dir_path = questions_dir or INTERVIEW_QUESTIONS_DIR
        self._cache: Optional[Dict[str, Any]] = None

    def get_data(self, force_refresh: bool = False) -> Dict[str, Any]:
        if self._cache is not None and not force_refresh:
            return self._cache

        directory = self.dir_path
        if not os.path.exists(directory):
            return {
                "companies": [],
                "stats": {"total_companies": 0, "total_rounds": 0, "total_questions": 0, "categories": {}},
                "all_categories": []
            }

        companies_map: Dict[str, Dict[str, Any]] = {}
        category_counts: Dict[str, int] = {}
        calendar_events: Dict[str, List[Dict[str, Any]]] = {}

        md_files = []
        for item in sorted(os.listdir(directory)):
            if item.endswith(".md"):
                md_files.append((item, os.path.join(directory, item)))

        for fname, fpath in md_files:
            try:
                with open(fpath, "r", encoding="utf-8", errors="ignore") as fp:
                    content = fp.read()
            except Exception:
                continue

            if "0. Basic" in fname or "0_1. General" in fname:
                self._parse_general_guide(fname, content, companies_map, category_counts)
            else:
                self._parse_company_interview(fname, content, companies_map, category_counts)

        # Finalize rounds list & categories
        for c in companies_map.values():
            c["categories"] = sorted(list(c["categories"]))
            if isinstance(c["rounds"], dict):
                r_list = []
                for r_name, r_data in c["rounds"].items():
                    r_data["categories"] = sorted(list(r_data["categories"]))
                    r_list.append(r_data)
                    
                    # Group into calendar if valid date exists
                    r_date = r_data.get("date", "")
                    if r_date and r_date not in ["Recent", "Core Reference"]:
                        # Extract YYYY-MM and date
                        clean_d = r_date.split()[0]
                        calendar_events.setdefault(clean_d, []).append({
                            "company": c["company_name"],
                            "round": r_name,
                            "date": r_date,
                            "question_count": len(r_data["questions"])
                        })
                c["rounds"] = r_list

        companies_list = list(companies_map.values())
        # Sort by recently added question banks (newest file_order first), then interview timestamp descending
        companies_list.sort(key=lambda c: (c.get("file_order", 0.0), c.get("timestamp", 0.0), c["company_name"].lower()), reverse=True)

        total_rounds = sum(len(c["rounds"]) for c in companies_list)
        total_questions = sum(c["total_questions"] for c in companies_list)

        # Prescribe standard categories ordering
        sorted_categories = []
        for cat in CATEGORIES_LIST:
            sorted_categories.append({
                "name": cat,
                "count": category_counts.get(cat, 0)
            })

        self._cache = {
            "companies": companies_list,
            "stats": {
                "total_companies": len(companies_list),
                "total_rounds": total_rounds,
                "total_questions": total_questions,
                "categories": category_counts,
                "tech_categories_count": len(category_counts)
            },
            "category_pills": sorted_categories,
            "calendar_events": calendar_events
        }
        return self._cache

    def _parse_company_interview(self, fname: str, content: str, companies_map: Dict[str, Any], category_counts: Dict[str, int]):
        lines = content.splitlines()
        om = re.search(r'^(\d+(?:_\d+)?)\.', fname)
        file_order = float(om.group(1).replace('_', '.')) if om else 0.0
        dm = re.search(r'(\d{1,2}-[A-Za-z]{3}-\d{4})', fname)
        file_date = dm.group(1) if dm else ""

        current_company_name = ""
        current_round_name = "Round 1"
        current_round_date = ""
        current_category = "General"
        current_q_text = ""
        current_answer_lines = []
        in_answer = False
        is_sub_q = False

        def push_question():
            nonlocal current_q_text, current_answer_lines, in_answer, is_sub_q, current_category, current_round_date
            if not current_q_text:
                return

            q_clean = re.sub(r'^\*+\s*(.*?)\s*\*+:', r'\1:', current_q_text.strip())
            q_clean = re.sub(r'^\*+|\*+$', '', q_clean).strip()
            q_clean = re.sub(r'^[●↳\s]+', '', q_clean).strip()
            q_clean = q_clean.replace('**', '').strip()
            if not q_clean:
                q_clean = current_q_text.strip()

            ans_clean = "\n".join(current_answer_lines).strip()
            ans_clean = re.sub(r'^(?:\*{0,2}Answer:\*{0,2}\s*)', '', ans_clean).strip()

            c_name = current_company_name or "General Company Interviews"
            r_name = current_round_name or "Technical Round"

            if not ans_clean or len(ans_clean) < 15:
                ans_clean = get_fallback_answer_for_question(q_clean, c_name, r_name)

            norm_cat = detect_category_from_text(q_clean, ans_clean, current_category)
            category_counts[norm_cat] = category_counts.get(norm_cat, 0) + 1

            round_date_val = current_round_date or file_date or "Recent"
            round_ts = parse_date_to_timestamp(round_date_val)

            if c_name not in companies_map:
                companies_map[c_name] = {
                    "company_name": c_name,
                    "rounds": {},
                    "total_questions": 0,
                    "categories": set(),
                    "latest_date": round_date_val,
                    "timestamp": round_ts,
                    "file_order": file_order,
                    "source_file": fname
                }
            else:
                companies_map[c_name]["file_order"] = max(companies_map[c_name].get("file_order", 0.0), file_order)
                if round_ts > companies_map[c_name].get("timestamp", 0.0) or not companies_map[c_name].get("latest_date"):
                    companies_map[c_name]["timestamp"] = round_ts
                    companies_map[c_name]["latest_date"] = round_date_val

            if r_name not in companies_map[c_name]["rounds"]:
                companies_map[c_name]["rounds"][r_name] = {
                    "round_name": r_name,
                    "date": round_date_val,
                    "timestamp": round_ts,
                    "questions": [],
                    "categories": set()
                }
            else:
                if round_date_val and (not companies_map[c_name]["rounds"][r_name].get("date") or round_ts > companies_map[c_name]["rounds"][r_name].get("timestamp", 0.0)):
                    companies_map[c_name]["rounds"][r_name]["date"] = round_date_val
                    companies_map[c_name]["rounds"][r_name]["timestamp"] = round_ts

            q_id = f"q_{len(category_counts)}_{sum(c.get('total_questions', 0) for c in companies_map.values())}"
            q_entry = {
                "id": q_id,
                "question": q_clean,
                "answer": ans_clean,
                "has_answer": bool(ans_clean),
                "is_sub_q": is_sub_q,
                "category": norm_cat,
                "source_file": fname
            }

            companies_map[c_name]["rounds"][r_name]["questions"].append(q_entry)
            companies_map[c_name]["rounds"][r_name]["categories"].add(norm_cat)
            companies_map[c_name]["categories"].add(norm_cat)
            companies_map[c_name]["total_questions"] += 1

            current_q_text = ""
            current_answer_lines = []
            in_answer = False
            is_sub_q = False

        for line in lines:
            line_str = line.strip()
            if not line_str:
                if in_answer:
                    current_answer_lines.append(line)
                continue

            m_date = re.search(r'\*?Date:\s*([^*]+?)\*?$', line_str, re.IGNORECASE)
            if m_date:
                current_round_date = m_date.group(1).strip()
                continue

            m_comp_details = re.search(r'<summary>\s*(?:<h2>)?\s*(?:!\[.*?\]\(.*?\))?\s*(?:🏢)?\s*([A-Za-z0-9\s\.\-_/&]+?)(?:</h2>)?\s*</summary>', line_str, re.IGNORECASE)
            if m_comp_details and not re.search(r'<summary>\s*<strong>', line_str):
                push_question()
                raw_c = m_comp_details.group(1).strip()
                if " - " in raw_c or r"\-" in raw_c:
                    parts = re.split(r'\s*(?:\\-|-|–)\s*', raw_c)
                    current_company_name = parts[0].strip()
                    if len(parts) > 1:
                        current_round_name = parts[1].strip()
                else:
                    current_company_name = raw_c
                current_round_date = ""
                current_category = "General"
                continue

            m_round_details = re.search(r'<summary>\s*(?:<h3>)?\s*([A-Za-z0-9\s\.\-_/&]+?)(?:</h3>)?\s*</summary>', line_str, re.IGNORECASE)
            if m_round_details and not re.search(r'<summary>\s*<strong>', line_str) and not m_comp_details:
                push_question()
                current_round_name = m_round_details.group(1).strip()
                current_round_date = ""
                current_category = "General"
                continue

            if ("🏢" in line_str and "**" in line_str) or re.match(r'^##\s+[A-Za-z0-9]', line_str):
                push_question()
                clean = line_str.replace("![🏢]()", "").replace("🏢", "").replace("*", "").replace("#", "").strip()
                clean = clean.replace(r"\-", "-").replace("–", "-")
                parts = [p.strip() for p in clean.split("-") if p.strip()]
                if parts:
                    current_company_name = parts[0]
                    current_round_name = " - ".join(parts[1:]) if len(parts) > 1 else "Level 1"
                current_round_date = ""
                current_category = "General"
                continue

            m_cat = re.search(r'【\s*(.+?)\s*】', line_str)
            if m_cat:
                push_question()
                current_category = m_cat.group(1).strip()
                continue

            m_q_summary = re.search(r'<summary>\s*<strong>\s*(.+?)\s*</strong>\s*</summary>', line_str, re.IGNORECASE)
            if m_q_summary:
                push_question()
                raw_q = m_q_summary.group(1).strip()
                if raw_q.startswith("↳"):
                    is_sub_q = True
                    raw_q = re.sub(r'^↳\s*(?:Follow-up:\s*)?', '', raw_q).strip()
                elif raw_q.startswith("●"):
                    is_sub_q = False
                    raw_q = re.sub(r'^●\s*', '', raw_q).strip()
                current_q_text = raw_q
                in_answer = True
                continue

            if line_str.startswith("</details>"):
                if in_answer:
                    push_question()
                continue

            if line_str.startswith("●") or line_str.startswith("↳"):
                push_question()
                is_sub = line_str.startswith("↳")
                q_text = line_str[1:].strip()
                q_text = re.sub(r'^\*+|\*+$', '', q_text).strip()
                current_q_text = q_text
                is_sub_q = is_sub
                in_answer = True
                continue

            if in_answer:
                current_answer_lines.append(line)

        push_question()

    def _parse_general_guide(self, fname: str, content: str, companies_map: Dict[str, Any], category_counts: Dict[str, int]):
        lines = content.splitlines()
        comp_name = "DevOps Core Fundamentals" if "0. Basic" in fname else "Production Scenarios & Strategic Recovery"
        current_round = "General Architecture & Behavioral"
        current_cat = "General"
        current_q_text = ""
        current_answer_lines = []
        in_answer = False

        def push_q():
            nonlocal current_q_text, current_answer_lines, in_answer, current_cat
            if not current_q_text:
                return
            ans_clean = "\n".join(current_answer_lines).strip()
            ans_clean = re.sub(r'^(?:\*{0,2}Answer:\*{0,2}\s*)', '', ans_clean).strip()
            q_clean = re.sub(r'^\*+|\*+$', '', current_q_text.strip()).strip()
            if not ans_clean or len(ans_clean) < 15:
                ans_clean = get_fallback_answer_for_question(q_clean, comp_name, current_round)

            norm_cat = detect_category_from_text(q_clean, ans_clean, current_cat)
            category_counts[norm_cat] = category_counts.get(norm_cat, 0) + 1

            q_id = f"gen_{len(category_counts)}_{sum(c.get('total_questions', 0) for c in companies_map.values())}"
            q_entry = {
                "id": q_id,
                "question": q_clean,
                "answer": ans_clean,
                "has_answer": bool(ans_clean),
                "is_sub_q": False,
                "category": norm_cat,
                "source_file": fname
            }

            file_order = 0.1 if "0_1" in fname else 0.0
            if comp_name not in companies_map:
                companies_map[comp_name] = {
                    "company_name": comp_name,
                    "rounds": {},
                    "total_questions": 0,
                    "categories": set(),
                    "latest_date": "Core Reference",
                    "timestamp": 0.0,
                    "file_order": file_order,
                    "source_file": fname
                }
            if current_round not in companies_map[comp_name]["rounds"]:
                companies_map[comp_name]["rounds"][current_round] = {
                    "round_name": current_round,
                    "date": "Core Reference",
                    "timestamp": 0.0,
                    "questions": [],
                    "categories": set()
                }
            companies_map[comp_name]["rounds"][current_round]["questions"].append(q_entry)
            companies_map[comp_name]["rounds"][current_round]["categories"].add(norm_cat)
            companies_map[comp_name]["categories"].add(norm_cat)
            companies_map[comp_name]["total_questions"] += 1

            current_q_text = ""
            current_answer_lines = []
            in_answer = False

        for line in lines:
            line_str = line.strip()
            if not line_str:
                if in_answer:
                    current_answer_lines.append(line)
                continue

            if line_str.startswith("## "):
                push_q()
                current_round = line_str[3:].strip()
                continue

            m_sum = re.search(r'<summary>\s*<strong>\s*(.+?)\s*</strong>\s*</summary>', line_str, re.IGNORECASE)
            if m_sum:
                push_q()
                raw_q = m_sum.group(1).strip()
                raw_q = re.sub(r'^\d+[\.\)]\s*', '', raw_q)
                current_q_text = raw_q
                in_answer = True
                continue

            if line_str.startswith("</details>"):
                if in_answer:
                    push_q()
                continue

            if in_answer:
                current_answer_lines.append(line)

        push_q()

question_bank_service = QuestionBankService()
