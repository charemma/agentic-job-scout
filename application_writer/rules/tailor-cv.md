# Tailor-CV Rule

Pragma fuer den `tailor-cv` Step im `apply` Flow, zusaetzlich zu den Default-Rules dieses Schritts.

## Eingaben

- Obsidian-Notiz, gefunden ueber `id: {{vars.id}}` im Frontmatter unter
  `~/Notes/1 Projects/Applications/`.
- Block `## Analyse/Fit` in derselben Notiz, mit:
  - `### Profilwahl` -- akzeptiert nur `pe` (Master-Profil).
  - `### CV-Verbesserungs-Vorschlaege` -- Bulletliste mit File:zeile-Ankern.
- Quell-Datei `profil.tex`.

## Ausgaben

- `bewerbungen/<id>/profil.tex` -- Kopie der Quelle, mit angewendeten
  Schaerfungen.
- `bewerbungen/<id>/Lebenslauf_Candidate_Name.pdf` -- via
  `just bewerbung::build <id>`.

## Filter-Regeln fuer `### CV-Verbesserungs-Vorschlaege`

Anwenden ("APPLY"):

- Anker matcht `profil.tex(:\\d+)?`.
- Bullet beschreibt eine Umformulierung oder Priorisierung vorhandener
  Inhalte (eine "Formulierungs-Idee" aus dem Analyse-Schritt).

Ueberspringen ("SKIP", begruendet im task-output):

- Anker zeigt auf `common/*.tex` (sidebar, experience, header, footer,
  preamble). Per Issue out of scope -- `common/` darf nicht geaendert
  werden, weil das alle Profile betrifft.
- Bullet hat einen Konjunktiv-Guard: "falls jemals genutzt", "sofern in
  den OSS-Repos eingesetzt", "wenn praktisch belegt", "wenn dabei
  eingesetzt", o.ae. Kein Beleg -> keine Aenderung.
- Bullet ohne klares File:zeile-Anker (frei laufender Text).
- Bullet, der eine neue Faehigkeit/Technologie einfuehrt, die nicht in
  `profil.tex` ODER `common/*.tex` bereits steht.

## No-Fabrication-Klausel

Eine Schaerfung ist legitim, wenn sie eine Faehigkeit, die the candidate laut
profile + common bereits hat, im Text staerker sichtbar macht -- durch
Reihenfolge, Wortwahl, oder explizites Benennen eines Synonyms.

Eine Schaerfung ist Erfindung und damit verboten, wenn sie:

- Eine Technologie / Tool / Sprache hinzufuegt, die weder in
  `profil.tex` noch in `common/*.tex` belegt ist.
- Eine Jahresangabe / Erfahrungsdauer aendert.
- Eine Rolle oder Position behauptet, die im CV nicht steht.

Im Zweifel: SKIP und im task-output dokumentieren.

## LaTeX-Escapes

Die Vorschlaege aus dem Analyse-Schritt sind reiner Text. Beim Einsetzen in `profil.tex` die
LaTeX-Sonderzeichen escapen, sonst bricht `lualatex`:

- `&` -> `\&`
- `%` -> `\%`
- `$` -> `\$`
- `#` -> `\#`
- `_` -> `\_` (ausserhalb von `\texttt`-Bloecken)

Nach jedem Edit `just bewerbung::build <id>` ausfuehren -- der Build ist
der schnellste Lackmus-Test fuer kaputte Escapes. Bei Fehler: aborted
mit stderr.

## Routing

- Erfolg (profil.tex + PDF beide vorhanden) -> `review`.
- `just bewerbung::build` exit != 0 -> `aborted`, stderr im
  Begruendungs-Feld.
- `## Analyse/Fit` oder `### Profilwahl` fehlt -> `aborted`,
  "Upstream-Invariante verletzt".
- `profil.tex` existiert nicht -> `aborted`.

## Task-Output Format

```
Geaendert/erzeugt:
- bewerbungen/<id>/profil.tex
- bewerbungen/<id>/Lebenslauf_Candidate_Name.pdf

Angewendete Schaerfungen:
- profil.tex:17 -- "Nix (Sprache & Flakes), NixOS" statt "NixOS, Nix Flakes"

Uebersprungene Bullets:
- sidebar.tex:4 -- Anker in common/, OUT per Issue
- profil.tex:19 -- Konjunktiv-Guard "falls jemals genutzt"
- experience.tex:6 -- Anker in common/, OUT per Issue
```

Kein "passt schon", kein implizites Skippen. Jeder Bullet ist
nachvollziehbar.
