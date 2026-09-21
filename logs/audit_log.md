# DevOps Hub Activity & Audit Log

This document serves as the continuous, human-readable system log persisted directly in the Git repository (`nagaraj602/devops-hub-app-with-interview-quest`). If the application, cluster, or server goes down, this log provides complete auditability and state history.

## Audit Log History

| Timestamp (IST) | Event | Target / Component | Details / Commit / Status | Triggered By |
| :--- | :--- | :--- | :--- | :--- |
| 2026-09-20 20:40:00 | System Initialization | Core Application | Initialized DevOps Hub App (Port 8926, Ubuntu Base) | System Setup |
| 2026-09-20 20:40:00 | Data Seed | Question Bank | Loaded 1269 Questions, 52 Companies, 70 Rounds, 18 Categories | Old IQ Loader |
| 2026-09-20 20:40:00 | Data Seed | Commands Cheatsheet | Loaded 16 Categories (Linux, K8s, Docker, Terraform, etc.) | Cheatsheet Loader |
| 2026-09-20 20:40:00 | Repo Linked | Training Materials | Configured live sync from https://github.com/artisantek/training-materials.git | System |
| 2026-09-20 20:40:00 | Repo Linked | Notes Repo | Configured live sync from https://github.com/nagaraj602/Notes.git | System |
| 2026-09-20 22:30:00 | Content Rewrite | Question Bank Answers | Rewrote 42 questions in Basic IQ and 7 in Part 2 with multi-method answers, scenarios, and pushed to Notes repo | Content Upgrade |
| 2026-09-20 22:35:00 | UI Overhaul | Project Architecture | Redesigned project page with top guide card, impact metrics, interactive sizing calculator, and prep accordions | UI Upgrade |
| 2026-09-20 22:40:00 | UI Polish | Navigation & App Logs | Added App Logs page with live Kubernetes vs Compose runtime detection and component health check; added SVG favicon | Feature Addition |
| 2026-09-20 22:50:00 | Feature Upgrade | Training Materials | Enabled combined multi-repo tree (ArtisanTek + Notes), debounced full-text search with match highlighting & floating navigator | Feature Addition |
| 2026-09-20 22:55:00 | Bugfix | Mermaid & Image Proxy | Sanitized Mermaid flowchart syntax, converted raw GitHub URLs to local /api/training/raw/ proxy endpoints | Bugfix |
| 2026-09-20 23:00:00 | Docker & K8s Rollout | Kubernetes Deployment | Built and pushed nagarajkamath602/devops-hub-app-with-interview-quest:latest, updated imagePullPolicy to Always, and verified rollout | Deployment |
| 2026-09-21 00:22:37 | Feature Update | Cost Optimization Scheduler & Multi-Method Q&As | Added 10:30 PM IST 30-minute countdown banner and enriched answers for 1050+ questions across Notes repo | Antigravity Assistant |
| 2026-09-21 12:15:00 | Release v1.0.1 | Cost Optimization Banner & UI Refinements | Refined cost optimization shutdown banner (no GCP/maintenance references), clickable deep-dive questions with chevrons, simplified EKS calculator at bottom, darker text, high-contrast code blocks, scroll reset, compact split calendar | Antigravity Assistant |
| 2026-09-21 14:40:00 | Release v1.0.2 | Vertical Stats Dock, Exact Project & Copy Buttons | Repositioned stat boxes into left vertical icon dock with hover flyouts, moved Calendar trigger to action toolbar, removed Tech Categories box, enabled frictionless company/round name text selection, wired 100% reliable question/answer copy buttons, and restored exact verbatim project content | Antigravity Assistant |
| 2026-09-21 15:15:00 | Release v1.0.3 | Flowchart Embedded Screenshots, Margin Fix, Calendar Current Date & Button Highlighting | Embedded screenshots natively in Mermaid flowchart, separated vertical dock with 80px margin, defaulted calendar to current date with full-size layout, enabled toggle release on favorites, and added dynamic active button highlighting | Antigravity Assistant |
| 2026-09-21 15:40:00 | Release v1.0.4 | Revert Calendar Button to Full-Size Stat Card & Restore Compact Split Calendar Modal | Reverted calendar button to original interactive stat card size/style at top of content, removed small calendar toolbar button, and restored compact split calendar layout with side-by-side day events panel | Antigravity Assistant |
| 2026-09-21 15:50:00 | Release v1.0.5 | Calendar Round Event Listing & Direct Round Navigation | Fixed calendar round listing on date click (resolved escapeHtml definition), added exact date parsing, and enabled direct navigation to expand and highlight selected company round in Question Bank | Antigravity Assistant |

## Active Repositories Monitored

1. **DevOps Hub App & Storage**: `https://github.com/nagaraj602/devops-hub-app-with-interview-quest.git` (Active Branch: `main`)
2. **Notes & Interview Questions**: `https://github.com/nagaraj602/Notes.git` (Active Branch: `main`)
3. **Training Materials**: `https://github.com/artisantek/training-materials.git` (Active Branch: `main`)


