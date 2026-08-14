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

## Beschaeftigungsform (Stand 2026-08)

the candidate ist nicht mehr nur an Freelance/Contracting interessiert, sondern seit
2026-08-12 explizit offen fuer **Festanstellung**, insbesondere Teilzeit
(50%) fuer 3-4 Monate mit Option auf 100% danach. Contracting bleibt weiter
attraktiv, ist aber nicht mehr die einzige akzeptierte Form -- beide
Beschaeftigungsformen werden gleichwertig bewertet, sofern die restlichen
Kriterien passen.

## Harte Bedingung: nur AI-Security

**Stand 2026-08-14, geaendert:** the candidate will nur noch Stellen mit klarem
AI-Security-Bezug. Vorher war AI-Security nur eine Praeferenz/Gewichtung
("Platform Engineering ohne AI-Security bleibt gueltig") -- das gilt nicht
mehr. Reine Platform-Engineering-, DevOps- oder klassische AppSec-Stellen
**ohne** AI-Security-Bezug sind ab jetzt **kein** gueltiger Match mehr,
auch wenn der technische Fit sonst exzellent ist. Diese Bedingung gilt
**fuer beide Beschaeftigungsformen** (Festanstellung wie Contracting) --
was sich je nach Beschaeftigungsform unterscheidet, ist NICHT ob
AI-Security noetig ist (immer ja), sondern was zusaetzlich noch hart
verlangt wird, siehe die beiden Unterabschnitte unten.

- **Hard-Gate**: Hat die Stellenbeschreibung keinen erkennbaren
  AI-Security-Bezug (LLM Security, Prompt Injection, AI Red Teaming,
  AI Governance/Compliance, MLSecOps, Model/Data Poisoning, AI Supply
  Chain Security, Security-Arbeit an/mit AI-Systemen oder -Infrastruktur)
  -- **`fit_level` maximal `schwach`**, unabhaengig von allem anderen.
  Klassische Application Security, generische IT-Security oder reines
  Platform Engineering/DevOps ohne AI-Bezug zaehlen NICHT als AI-Security,
  auch wenn "Security" im Titel steht.
- Bei echtem AI-Security-Bezug: sein OSCP + Bug-Bounty-Hintergrund plus
  praktische LLM/Agent-Erfahrung (Claude, MCP, kuromaku) ist ein echter
  Beleg, entsprechend selbstbewusst bewerten -- Tool-Luecken sind hier
  keine Disqualifikation.

### Bei Contracting/Freelancing: Kombi mit DevOps/Platform Engineering gewuenscht

AI-Security kombiniert mit DevOps oder Platform Engineering ist der
**Wunschfall**, nicht nur "toleriert" (z.B. "Platform Engineer mit
AI-Security-Anteil", "Security Engineer fuer AI/LLM-Infrastruktur",
"DevOps mit MLSecOps-Fokus"). AI-Security bleibt trotzdem Pflicht (siehe
Hard-Gate oben) -- diese Kombination ist einfach das Profil, das am besten
zu the candidate passt, entsprechend hoch bewerten wenn beides erkennbar ist.

### Bei Festanstellung: AI-Security UND volles Remote, beides hart

**Stand 2026-08-14, praezisiert:** Fuer Festanstellungs-Positionen muessen
**beide** Bedingungen gleichzeitig erfuellt sein -- AI-Security-Bezug
(Hard-Gate oben) UND volles Remote. Kein Hybrid, keine Vor-Ort-Pflicht,
auch nicht "2 Tage/Woche im Büro". Faellt eine der beiden Bedingungen weg,
gilt der Match nicht, unabhaengig vom sonstigen technischen Fit.

- Steht in der Stellenbeschreibung explizit Hybrid- oder Vor-Ort-Pflicht bei
  einer Festanstellung: **`fit_level` maximal `schwach`**, unabhaengig davon
  wie gut der technische Fit sonst ist. Das ist ein Hard-Cap, keine
  Abwaegung -- und kommt zusaetzlich zum AI-Security-Hard-Gate oben, nicht
  anstelle davon.
- Bei Contracting-Projekten gilt diese Remote-Regel nicht als eigener
  Hard-Cap (dort war Remote schon vorher ueber `remoteInPercent` im
  Portal-Filter abgedeckt) -- die Unterscheidung ist: Festanstellung =
  Remote hart, Contracting = wie gehabt ueber den Portal-Filter.
- Ist der Remote-Status in der Ausschreibung unklar/nicht genannt: nicht
  automatisch disqualifizieren, aber im `summary` explizit als offene Frage
  benennen ("Remote-Modell nicht spezifiziert -- pruefen").

## Positives Signal: EU-weit / nicht auf Deutschland begrenzt

Wenn eine Stelle explizit **EU-weit** oder nicht auf Deutschland beschraenkt
ausgeschrieben ist (z.B. "remote across the EU", "any EU country",
kein Wohnsitz-/Arbeitsort-Zwang auf DE) -- das ist ein **"Jackpot"**-Signal.
Im `summary`-Feld explizit hervorheben (z.B. "EU-weit ausgeschrieben --
Jackpot-Signal"), damit es in der ntfy-Notification sichtbar landet und
the candidate es auf den ersten Blick erkennt, ohne die volle Ausschreibung lesen zu
muessen.

## Was er NICHT macht

- Reine Frontend-Entwicklung (React, Vue, Angular)
- Pure Datenanalyse / ML-Modellierung (ML-Research, kein Engineering-Setup)
- Sales / Business Development -- er ist Engineer, kein Salesman
- Compliance-Beratung ausserhalb seiner technischen Domain (er IST kein Auditor)
