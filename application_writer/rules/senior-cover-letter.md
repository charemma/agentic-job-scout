# Senior Cover Letter

Schreib wie ein Senior-Engineer der ueber Werkstoff redet. Ruhig, knapp, eine Sache nach der anderen. Der Leser soll am Ende denken "den will ich sprechen", ohne dass irgendwo "warum mich nehmen" steht.

## Grundregel: weniger Text

- **120-150 Worte. Hartes Ziel.** Mehr als 150 = du machst es falsch. Zaehle bevor du absendest.
- **Drei Absaetze, nicht fuenf.** Identitaet+Projekt, Scope, Abschluss.
- **Opener-Absatz: max 50 Worte.** Wer du bist + zuletzt + ein Bezug zur Stelle. Mehr nicht.
- **EIN konkretes Projekt-Beispiel.** Verschmilz es mit dem Identitaets-Anker, nicht als eigener Absatz mit eigener Story-Setup.
- **Maximal 2 Tools/Technologien in einem Satz.** Kein Stacking.
- **Keine Brueckensaetze.** "Meine Staerke liegt dort, wo..." / "Das passt zu..." / "Dazu gehoeren..." -- streichen. Wenn du den Punkt nicht direkt sagen kannst, ist er nicht der Punkt.

## Was rein muss

1. **Rollen-Anker, nicht Biographie-Anker** (1-2 Saetze). Der erste Satz muss zur **gesuchten Rolle** sprechen, nicht zu deiner letzten Station. Was kann diese Rolle? Was ist der Kern der Stelle? Du verbindest deine Identitaet mit DEM, was die Stelle braucht -- nicht mit deinem letzten Projekt.
   - Stelle Linux-Architekt? -> Linux-Infrastruktur architektonisch denken
   - Stelle DevOps-Engineer? -> Plattform-Aufbau und Automatisierung
   - Stelle Security-Engineer? -> Security im Produktiv-Kontext
   Das letzte Projekt kommt **erst danach** als Beleg.
2. **Ein Projekt-Beispiel** (1-2 Saetze): konkret, eine Sache, kein Tool-Cluster. Das Projekt belegt was du im Opener gesagt hast -- wenn das Projekt nicht zum Rollen-Anker passt, ist es das falsche Projekt fuer dieses Anschreiben. Waehl ein passenderes aus common/experience.tex.
3. **Luecke + Rate + Verfuegbarkeit** (kurz): falls echte Luecke -- ein Satz. Rate aus Frontmatter. Verfuegbarkeit. Name.

**Anti-Schablone:** Wenn jeder Opener bei dir mit "ich bin Plattform-Engineer mit Schwerpunkt X, zuletzt im Umfeld Y" anfaengt -- egal welche Stelle -- machst du es falsch. Variiere mit dem Rollen-Anker.

## Confidence-Kalibrierung (wichtig)

Sprich so selbstbewusst wie der echte Fit es traegt. Untertreibung ist genauso falsch wie Uebertreibung. Lies das Mapping in `## Analyse/Fit` und kalibriere:

| Fit-Level (aus Analyse/Fit) | Sprache fuer den Match | Beispiel |
|------------------------------|------------------------|----------|
| Sehr starker / 1:1-Match | "starker Fit", "klarer Match", "genau das was ich tue", "sehr gut" | "Der Tech-Stack passt sehr gut: k3s, Pulumi, GitLab CI und Security-Hardening gehoeren zu meinem Tagesgeschaeft." |
| Solider Fit, ein paar Luecken | "guter Fit", "mein Hebel liegt bei X", "passt gut" + ehrliches Scope | "Plattform und Security sind ein klarer Fit; bei <Tool X> bringe ich die Anschlussstellen statt der Produkterfahrung." |
| Schwacher / Teil-Fit | "passt fuer Teil X", "mein Beitrag liegt bei", "Schwerpunkt fuer mich waere" + ehrliche Scope-Cut | "Mein Beitrag liegt bei Plattform und Security; React und Supabase sind nicht mein Feld." |

**Faustregel:** "gut" ist der Default-Floor. Bei echtem starken Match steig auf "sehr gut" / "stark". Bei schwachem Match formulier ehrlich, NICHT mit "gut" beschoenigend. Lies das Gesamtbild im Mapping und ueberzeichne nicht.

Was NICHT geht: weak-fit Stelle mit "starker Match" verkaufen. Ehrlichkeit traegt Souveraenitaet -- nicht andersherum.

## Verb-Praezision

Generische Verben verkaufen die eigene Arbeit unter Wert. Wenn Domain-spezifisches Vokabular existiert, nutz es.

| Generisch (vermeiden) | Domain-spezifisch (verwenden) |
|------------------------|--------------------------------|
| geprueft / angeschaut | auf Schwachstellen analysiert / aus offensiver Sicht reviewt / im Threat-Model durchgegangen |
| Massnahmen abgeleitet | Hardening-Massnahmen abgeleitet / Pentest-Findings in Fixes ueberfuehrt |
| gearbeitet mit | gebaut / aufgebaut / betrieben / abgesichert / geliefert |
| beschaeftigt mit | verantwortet / geleitet / aufgesetzt |
| kuemmere mich um | trage / loese / steuere |

Im Security-Kontext speziell: nenn was untersucht wurde (Schwachstellen, Authentication-Flows, Container-Surfaces, Secrets-Handling) und was rausgekommen ist (Hardening, Disclosure, Fixes) -- nicht nur "Security gemacht".

## Was NICHT rein darf

- **Meta-Erklaerungen.** "Das ist die Arbeit die zaehlt", "Gerade bei einem Relaunch ist X wichtiger als Y", "Aus regulierten Umgebungen kenne ich die Disziplin...". Du sagst NICHT was zaehlt -- du tust es.
- **Keyword-Listen.** "DevOps, Docker, Linux, Security, Migration" in einem Satz: weg. Maximal zwei Begriffe, dann Punkt.
- **Mehrere Projekte hintereinander.** "Bei A habe ich X. Bei B habe ich Y." liest sich wie CV. EIN Projekt, ein Satz, fertig.
- **Negative Opener.** "Security bringe ich nicht als Checklisten-Thema..." -- streichen. Positiv schreiben oder weglassen.
- **Konjunktiv-Cluster.** "wuerde", "koennte", "moechte" als Default. Aktiv: "loese", "baue", "trage".
- **Kundennamen.** Anonymisiert auf Branche/Domain.

## Beispiel-Form (Richtwert, nicht Schablone)

Vier Bloecke, kurz:

> Sehr geehrter Herr <Nachname>,
>
> [1-2 Saetze Identitaet. Wer, was, wo zuletzt. Direkter Bezug zur Stelle.]
>
> [1-2 Saetze EIN Projekt. Konkret, anonymisiert. Keine Tool-Liste.]
>
> [Falls echte Luecke: 1 Satz, aktiv formuliert. Plus Rate, Verfuegbarkeit. Plus Name.]
>
> Mit freundlichen Gruessen
> the candidate

## Gute Beispiele (variieren mit dem Rollen-Anker)

### Beispiel: Linux-Architekt-Stelle (Konzeption/Doku-fokussiert)

> Sehr geehrte Frau Sonneck,
>
> Linux-Infrastrukturen architektonisch zu fassen -- modulare, austauschbare, sichere Plattformen mit klaren Betriebsmodellen und sauberer Doku -- ist die Arbeit, in der ich die letzten Jahre angekommen bin. Genau das suchen Sie.
>
> Mein Hebel liegt bei Konzept, Hardening und Uebergabe in den Betrieb. Bei einem Kunden im regulierten Umfeld habe ich eine Plattform auf k3s aufgebaut und mit Ansible automatisiert -- als belegbares Beispiel fuer "Architektur trifft Operating Model", nicht als Tech-Stack-Showcase. RHEL und SLES ordne ich als Implementierungsbausteine ein; jahrelange Distribution-Tiefenexpertise bringe ich nicht mit.
>
> Verfuegbar zum Projektstart 07/2026, Auslastung im Gespraech. Stundensatz <X> EUR netto remote, <Y> EUR netto onsite.
>
> Mit freundlichen Gruessen
> the candidate

Warum gut: Opener spricht **zur Rolle** ("Linux-Infrastrukturen architektonisch zu fassen"), nicht zur eigenen Bio. k3s-Projekt kommt erst danach als BELEG, nicht als Identitaets-Aufmacher.

### Beispiel: DevOps-Stelle (Plattform/Deployment-fokussiert)

> Sehr geehrter Herr Michael,
>
> Plattformen aufbauen, betreiben und absichern -- besonders dort wo Migrationen, Docker-Deployments und Hardening parallel laufen muessen -- ist mein Tagesgeschaeft.
>
> Bei einem Kunden im regulierten Umfeld habe ich eine Remote-Entwicklungsplattform auf k3s aufgebaut, automatisiert mit Pulumi und Ansible, inklusive Container-Hardening und Security-Reviews. Fuer Ihren Relaunch sehe ich den Hebel bei Plattform, Deployment und Security. React und Supabase sind nicht mein Feld; alles drumherum schon.
>
> Verfuegbar ab sofort, ca. 20 Stunden pro Woche, remote. Stundensatz <X> EUR netto.
>
> Mit freundlichen Gruessen
> the candidate

Warum gut: Opener bedient die DevOps-Rolle, k3s-Projekt belegt das. Beide Anschreiben starten unterschiedlich, weil die Rollen unterschiedlich sind.

## Anti-Beispiel: Schablonen-Opener

> ich bin Plattform-Engineer mit Schwerpunkt auf reproduzierbaren Linux- und NixOS-Setups, zuletzt im regulierten Medizintechnik-Umfeld.

Warum schlecht: gleiche Schablone egal welche Stelle. Liest sich wie LinkedIn-Bio, nicht wie Antwort auf die Ausschreibung. Das letzte Projekt + die letzte Branche gehoert in den Beleg, nicht in den Aufmacher.

## Schlechtes Beispiel

> Sehr geehrter Herr Michael,
>
> Plattformen aufbauen, betreiben und absichern ist mein Tagesgeschaeft, zuletzt im regulierten Medizintechnik-Umfeld. Die Schnittmenge aus DevOps, Docker/Linux-Betrieb, Security-Hardening und Migrationen passt zum Infrastruktur- und Plattform-Relaunch Ihres Kunden.
>
> Bei einem Kamera-Hersteller habe ich eine Jenkins-zu-GitLab-CI-Migration begleitet und Docker-basierte Remote-Entwicklungsumgebungen eingefuehrt. Im Medizintechnik-Umfeld habe ich eine Remote-Entwicklungsplattform mit Coder auf k3s aufgebaut, automatisiert ueber Pulumi und Ansible, dazu DevContainer modernisiert und Monorepos fuer selektive Builds optimiert. Das ist die Arbeit, die bei Relaunches zaehlt: reproduzierbare Deployments, klare Betriebsmodelle und weniger Reibung fuer Entwicklerteams.
>
> Security bringe ich nicht als Checklisten-Thema mit. OSCP, Bug-Bounty- und Responsible-Disclosure-Erfahrung sowie konkrete Reviews interner Web-Applikationen und Container-Infrastruktur gehoeren zu meinem Profil. In Projekten leite ich daraus praktische Massnahmen ab: haertere Base-Images, Least Privilege, sauberes Secrets-Handling, Security Gates und belastbare CI/CD-Bausteine.
>
> [...]

Warum schlecht: 6 Absaetze, zwei Projekte hintereinander aufgelistet ("Bei X habe ich, im Y habe ich"), drei Mal Keyword-Liste mit 4+ Tools, zweimal Meta-Erklaerung ("Das ist die Arbeit die zaehlt", "Security bringe ich nicht als Checklisten-Thema"), Negativ-Opener im Security-Absatz. Liest sich wie CV mit Verbindungssaetzen.

## Anti-Patterns (sehr knapp)

- "Mit grossem Interesse" / "Ich brenne fuer" / "passioniert" / "innovativ" als leeres Adjektiv
- "wuerde", "koennte", "moechte" als Default-Modus
- Tool-Listen mit 3+ Begriffen
- "Das ist die Arbeit die zaehlt" / "Gerade bei X ist Y wichtiger als Z" -- Meta-Erklaerung
- Konkrete Firmennamen

## Stundensatz

Aus Frontmatter `stundensatz:` Feld direkt ins Anschreiben. Range nach oben verankern (statt "80-95" -> "85 EUR netto" oder "90-95 EUR netto"). Nie weglassen.

## Checkliste

- Unter 200 Worten?
- Genau ein Projekt-Beispiel, nicht zwei?
- Keine Tool-Liste mit 3+ Begriffen?
- Keine Meta-Erklaerung ("das ist die Arbeit, die zaehlt")?
- Stundensatz und Name am Ende?
