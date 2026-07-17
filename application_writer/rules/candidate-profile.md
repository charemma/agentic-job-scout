# the candidate Background

Hintergrund-Profil zu the candidate (the candidate). Lies das, bevor du sein Profil gegen eine Stellenbeschreibung mappst -- nicht alles steht 1:1 im CV, vieles ist emergent ueber Stationen oder OSS-Arbeit.

Diese Datei lebt im cv repo (`.kuro/rules/`), damit sie auch ohne den `agent/` Seed-Cascade funktioniert.

## Identitaet (Kurz)

- Senior Platform / DevOps / Security Engineer
- ~20 Jahre Linux-Erfahrung, davon viele Jahre in regulierten Umgebungen
- Freelancer, Schwerpunkt Plattform-Engineering und Security
- Deutsch im Gespraech, Englisch in Code/Commits/Docs

## Technisches Fundament

**Linux & Betriebssysteme:**
- Debian/Ubuntu seit ueber 20 Jahren
- NixOS deklarativ, Multi-Host-Konfiguration in eigenen OSS-Projekten
- Embedded-Linux (Yocto-Stacks, Cross-Compilation)

**Container & Orchestrierung:**
- Docker fuer Deployment, Development, Sandboxing (langjaehrig)
- Kubernetes, k3s (Plattform-Aufbau, Operations)

**CI/CD & IaC:**
- GitLab CI (Migration Jenkins -> GitLab gefuehrt), GitHub Actions, Jenkins, Dagger
- Pulumi, Terraform, Ansible -- declarative ueber imperative
- Nix Flakes fuer reproduzierbare Builds

**Sprachen:**
- Python 15+ Jahre (Tooling, Integrationen, Automation)
- Rust (eigenes OSS-Projekt kuromaku)
- Go (Microservices)
- Bash (CLI-Tooling)

**Security:**
- OSCP zertifiziert
- Bug Bounty / Responsible Disclosure (HackerOne, Bundeswehr)
- Web Application Security: OWASP, Burp/ZAP, Pentest, Threat Modeling
- Container-Hardening, Base-Image-Slimming, Secrets Management
- Security Gates / SAST / SCA / SBOM in CI/CD

**Regulatorisches:**
- IEC 62304 Medizintechnik (Audit, Nachvollziehbarkeit)

**AI / LLM:**
- Praktische Erfahrung mit Claude, OpenAI/codex, Ollama
- MCP, Agent-Workflows
- Eigenes OSS-Projekt: kuromaku (Rust CLI fuer reproduzierbare AI-Agenten-Teams)
- AI-Tooling Beratung bei Client A (Claude Code + Copilot in DevContainer-Workflows)

## Open Source / Eigene Projekte

- **kuromaku** (Rust): CLI fuer reproduzierbare AI-Agenten-Teams mit YAML-Graphen, deterministischem Audit-Trail
- **Multi-Host-NixOS-Konfiguration** (deklarativ, ueber mehrere Hosts)
- **Gehaertete NixOS-IoT-Plattform** mit Nix Flakes und Cross-Compilation
- Diverse Tooling-Projekte (Anker fuer Workday-Tracking, etc.)

## Wie the candidate arbeitet (Cross-Cutting Strengths)

Diese Themen entstehen emergent aus seinen Stationen, nicht aus einer einzelnen CV-Zeile:

- **Plattform-Denke**: Aufbau + Betrieb + Hardening parallel. Nicht "kennt Tool X" sondern "baut, betreibt und sichert Plattformen ab ueber mehrere Stationen". Self-Service-Modelle, Coder/DevContainer-Umgebungen, Operating-Model-Definition.
- **Security durchgaengig**: OSCP ist kein Zertifikats-Bullet, sondern fliesst direkt in Plattform-Arbeit ein. Web-Reviews, Container-Hardening, Disclosure-Praxis -- alles am Produkt, nicht als isoliertes Hobby.
- **Automatisierung als Leitprinzip**: Wenn er etwas zweimal macht, scripted er's. just > nix > make > shell. Pulumi, Ansible, Dagger ueber alle Stationen.
- **Reproduzierbarkeit obsessiv**: Nix Flakes, deterministic builds, versioned configs. Same inputs = same outputs.
- **Architektur-Denken**: Systeme statt Features. "Was passiert wenn jemand das zweite oder dritte davon anlegt?" ist Standardfrage. Design fuer N von Anfang an.
- **Knapp und direkt**: "schrott" wenn schrott, "gut" wenn gut. Keine Diplomatie-Polsterung. Pragmatik vor Eleganz.

## Wichtige Faktoren fuer Match-Analyse

Wenn du the candidate gegen eine Stellenbeschreibung mappst:

1. **Domain vor Tool**: Konkrete Tools (Colmena, NixOps, Coolify, etc.) sind 2-3 Wochen Ramp-Up. Wenn die Core-Domain (NixOS, Platform Engineering, Container-Orchestrierung, Security) belegt ist, ist the candidate im Fit -- Tool-Gaps sind keine Disqualifikation.
2. **OSS und Eigenarbeit gilt**: NixOS-Erfahrung ist nicht nur in Kundenprojekten belegt, sondern in seinen eigenen OSS-Repos. Das ist gleich-wertig als Beleg, nicht "nur Hobby".
3. **Security ist Querschnitt**: Wenn die Stelle Security nennt, ist das fuer the candidate kein Bonus-Skill, sondern in seine Plattform-Arbeit eingebaut -- entsprechend selbstbewusst kalibrieren.
4. **Frontend = Luecke**: React, Vue, Svelte und moderne BaaS-Stacks (Supabase, Firebase) hat er nicht. Bei solchen Stellen ist der Fit klar geschnitten ("Backend/Plattform-Seite, Frontend nicht im Profil").

## Was er NICHT macht

- Reine Frontend-Entwicklung (React, Vue, Angular)
- Pure Datenanalyse / ML-Modellierung (ML-Research, kein Engineering-Setup)
- Sales / Business Development -- er ist Engineer, kein Salesman
- Compliance-Beratung ausserhalb seiner technischen Domain (er IST kein Auditor)
