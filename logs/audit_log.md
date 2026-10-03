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
| 2026-09-21 16:10:00 | Release v1.0.6 | Custom Repo Reordering & Deletion in Training Materials | Added move up/down controls, drag-and-drop reordering, repo management modal, and removal of custom repositories from session with confirmation | Antigravity Assistant |
| 2026-09-21 16:38:00 | Release v1.0.7 | Project Page Callout Prompt Boxes & Verbatim Highlight Styling | Added dedicated callout box for interview question variations inside Introduction accordion, enabled safe HTML rendering for overview/results highlights, and bolded technical keywords | Antigravity Assistant |
| 2026-09-21 17:05:00 | Release v1.0.8 | Planview Level 1 Q&As & Streamline Training Tree Actions | Added comprehensive multi-method answers for Planview Level 1 (21-Sep-2026) in Notes & app, and removed inline tree action buttons in favor of the Reorder modal | Antigravity Assistant |

## Active Repositories Monitored

1. **DevOps Hub App & Storage**: `https://github.com/nagaraj602/devops-hub-app-with-interview-quest.git` (Active Branch: `main`)
2. **Notes & Interview Questions**: `https://github.com/nagaraj602/Notes.git` (Active Branch: `main`)
3. **Training Materials**: `https://github.com/artisantek/training-materials.git` (Active Branch: `main`)


| 2026-09-21 20:21:37 | Feature Update (v1.0.9) | Performance & Bug Fixes | Added GZip compression, static cache headers, round toggle icon rotation fix, and deep-dive answer copy fix | Antigravity CLI |
| 2026-09-21 21:44:15 | Page Visibility Changed | Menu: Training Materials | Status set to Hidden (Unpublished) (previous: Published) | Admin Portal (Web UI) |
| 2026-09-21 21:44:28 | Page Visibility Changed | Menu: Training Materials | Status set to Hidden (Unpublished) (previous: Hidden) | Admin Portal (Web UI) |
| 2026-09-21 21:44:29 | Page Visibility Changed | Menu: Training Materials | Status set to Published (Active) (previous: Hidden) | Admin Portal (Web UI) |
| 2026-09-21 21:44:29 | Page Visibility Changed | Menu: Question Bank | Status set to Hidden (Unpublished) (previous: Published) | Admin Portal (Web UI) |
| 2026-09-21 21:44:29 | Page Visibility Changed | Menu: Question Bank | Status set to Published (Active) (previous: Hidden) | Admin Portal (Web UI) |
| 2026-09-21 21:45:00 | Release v1.0.10 | Hidden Admin Portal & Dynamic Page Visibility | Added private Admin Portal at port 9256 & admin.sidorea.shop with publish/unpublished toggles for Question Bank, Project, Training, Cheatsheets, and App Logs with friendly 403 notices and zero external DB | Antigravity Assistant |
| 2026-09-21 22:57:36 | Page Visibility Changed | Menu: Training Materials | Status set to Hidden (Unpublished) (previous: Published) | Admin Portal (Web UI) |
| 2026-09-21 22:57:36 | Page Visibility Changed | Menu: Training Materials | Status set to Published (Active) (previous: Hidden) | Admin Portal (Web UI) |
| 2026-09-21 23:00:00 | Release v1.0.11 | Admin Port Separation & Path Isolation | Restricted admin dashboard exclusively to port 9256 & admin.sidorea.shop root / without /admin prefix; blocked /admin on public port 8926 (returns 404) | Antigravity Assistant |
| 2026-10-02 12:15:00 | Release v1.0.16 | Update 21: 2-Button Toggle Controls, Top Calendar Toolbar & Load More Chunking | Replaced 4 expand/collapse buttons with 2 unified toggle buttons (Expand/Collapse All & Expand/Collapse Answers), relocated search/sort and toggle buttons next to Calendar card in a 2-row toolbar, and added 10-company progressive chunking with 'Load more \/' button | Antigravity Assistant |
| 2026-10-03 14:10:00 | Release v1.0.15 | Update 21 Refinements, Same-Line Toolbar & 10-Chunk Load More | Placed Question Bank controls directly in the same line as Calendar card, removed 1024px column breakpoint, removed content-visibility auto (preventing blank rows), enabled 10-company chunking with prominent 'Load more...' dropdown button, updated shutdown window to 12:00 AM - 5:30 AM IST, and deployed to docker compose | Antigravity Assistant |
| 2026-10-03 15:30:00 | Release v1.0.15 | Native 90% Zoom Visual Emulation, Expanded Side Margins & Controls Styling | Scaled root and preset base font size down by ~10% (15px to 13.8px) across all typography via rem units, added spacious left/right container padding and question body margins (110px left / 2.75rem right), removed Load More button borders into clean text link, set 4s toast duration, and rebuilt on docker compose | Antigravity Assistant |
| 2026-10-03 15:45:00 | Release v1.0.15 | Sort Dropdown Light-Scheme Fix & Instant Filter Performance Optimization | Removed redundant '(Default)' text from Sort option, added light color-scheme to prevent dark/blank popup rendering across all OS/browser themes, and added fast-path lazy evaluation in applyFilters (0ms execution time, completely eliminating 2-3s main-thread freeze on dropdown load) | Antigravity Assistant |
| 2026-10-03 16:10:00 | Release v1.0.15 | ArtisanTek Training Materials Sync & In-Memory Tree Auto-Healing | Baked ArtisanTek curriculum (AWS, Jenkins, Kubernetes, Linux modules) directly into container content directory, hooked training_service.invalidate_cache() into sync_training_repo and sync_notes_repo, and added auto-healing re-scan logic to prevent stale empty-tree caching | Antigravity Assistant |
| 2026-10-03 18:35:00 | Release v1.0.16 | Question Bank Chunking, Partials Modularization, Dynamic Mermaid & Sync Cache | Modularized question bank company cards into Jinja partial, implemented server-side filter and chunk pagination API with calendar auto-fetch banner, lazy-loaded Mermaid.js dynamically on demand, and added 30s TTL in-memory caching for sync and audit log views | Antigravity Assistant |
| 2026-10-03 19:15:00 | Release v1.0.16 | Custom Sort Dropdown Component & White Background Loading State | Replaced native OS select with pure-HTML custom dropdown component (eliminating Windows Chromium OS popup delay and black blank rectangle), added instant white background loading card with animated spinner during question bank sorting and filtering, and bumped static assets to v1.0.16.1 | Antigravity Assistant |
| 2026-10-03 19:30:00 | Release v1.0.16 | Accordion State & Expand Toggle Button 100% Synchronization | Synchronized Expand/Collapse All toggle button with category filtering, auto-updating button text/icon to 'Collapse All' when entering specific categories, restoring clean collapsed mode and 'Expand All' on Category 'All', and eliminating double-click requirement | Antigravity Assistant |






