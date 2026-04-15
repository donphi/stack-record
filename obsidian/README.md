# Obsidian Writing Environment for Stack Record

Write, preview, and push Stack Record notes from Obsidian with one-hotkey
note creation, LLM writing assistance, and broken-link validation.

## 1. Quick start

### Install Obsidian

Download from [obsidian.md/download](https://obsidian.md/download) or:

```bash
# Linux
sudo snap install obsidian --classic

# Linux (AppImage — manual download from obsidian.md/download)
chmod +x ./Obsidian-*.AppImage
./Obsidian-*.AppImage --no-sandbox

# macOS
brew install --cask obsidian
```
> **Note:** First launch may log `ENOENT: obsidian.json` (created automatically)
> and `vaInitialize failed` (harmless — GPU video decode probe). Both are safe to ignore.

### Open the vault

1. Launch Obsidian
2. Click **Open folder as vault**
3. Navigate to this repo and select `obsidian/`

The `obsidian/` folder is the vault root. Content folders (`concepts/`,
`methods/`, etc.) are symlinks pointing to `content-src/docs/` — edits go
directly to the real files, and git sees normal changes in `content-src/docs/`.
Obsidian-specific folders (`scripts/`, `copilot/`, `.obsidian/`) live here
natively, keeping `content-src/docs/` clean for Fumadocs.

### Install plugins (6 required)

Go to **Settings (Bottom Left) > Community plugins > Turn on community plugins > Browse**
and install:

| Plugin | Purpose |
|--------|---------|
| **Templater** | One-hotkey note pair creation |
| **Copilot** | LLM chat with vault-aware context |
| **mdx as md** (or "Edit MDX") | Treats `.mdx` as markdown for preview and wikilinks |
| **Find orphaned files and broken links** (or "Broken Links Cleaner") | Finds `[[wikilinks]]` pointing to non-existent files |
| **git** | Commit and push from inside Obsidian (optional - Only works on Desktop) |
| **Custom File Extensions and Types** | Makes `.meta.json` and `.template` files visible in sidebar |

Enable each plugin after installing.

---

## 2. Plugin configuration

### Templater
1. **Settings > Templater > Template folder location**: set to `scripts/`
2. **Settings > Templater > User script functions > Script files folder location**: set to `scripts/`
3. **Settings > Templater > Template hotkeys**: type `scripts/_new-note.md`
   and click **⊕** — this registers the command **Templater: Insert _new-note**

You can now trigger the script three ways:

| Method | Desktop | Mobile |
|--------|---------|--------|
| **Command palette** | `Ctrl+P` → "Templater: Insert _new-note" | Swipe down or tap menu → search "Templater" |
| **Ribbon icon** | Click the `<%` icon in the left sidebar → select `_new-note` | Same |
| **Keyboard hotkey** | **Settings > Hotkeys** → find "Templater: Insert _new-note" → click **⊕** → press shortcut | N/A |
| **Mobile toolbar** | N/A | **Settings > Mobile > Manage toolbar options > Add global command** → "Templater: Insert _new-note" |

> **Note:** The examples below use `Ctrl+Shift+N` as the shortcut. Substitute
> your chosen method if you prefer the command palette or ribbon icon.

The `_new-note.md` template is a one-line trigger that calls
`create-note-pair.js` via Templater's user script system. The script
prompts for note type, subfolder, slug, title, description, domain code,
and ID number, then creates a folder containing `index.mdx` and
`index.meta.json` from the correct `_template/`, and opens `index.mdx`
for editing.

### Copilot + OpenRouter

1. **Settings > Copilot > Basic > Set Keys**
2. Select **OpenRouter** as provider
3. Paste your OpenRouter API key (get one at [openrouter.ai/keys](https://openrouter.ai/keys))
4. **Settings > Copilot > Model > Add Custom Model**:
   - Provider: **OpenRouter**
   - Model: `anthropic/claude-sonnet-4` (or any model you prefer)
   - Enable **CORS** if you get connection errors
5. **Settings > Copilot > QA**: toggle **Vault QA Mode** on and let it index

### mdx-as-md-obsidian

No configuration needed after install. `.mdx` files will render as markdown
with preview, wikilink resolution, and syntax highlighting.

### Custom File Extensions and Types

The `.template` files inside each `_template/` folder are invisible by default
because Obsidian does not recognise the extension. Add it manually:

1. **Settings > Custom File Extensions Plugin > Config**: the text area
   contains a JSON object with a `markdown` array. Add `"template"` to the end
   of the array (after the last existing entry, e.g. `"html"`)
2. The **Active View Types and Extensions** list at the bottom of the settings
   page should now show `template` in the **markdown** row
3. Restart Obsidian — `example.mdx.template` files now appear in the sidebar
   and open as markdown

### obsidian-git (optional)

1. **Settings > obsidian-git > Authentication**: enter your GitHub username
   and a Personal Access Token
2. Set **Auto pull interval** and **Auto push interval** to your preference
   (e.g. 5 minutes) or leave manual
3. Use the command palette: "obsidian-git: Commit and push"

---

## 3. Creating a new note

Trigger **Templater: Insert _new-note** using any method from
[Section 2](#templater) (command palette, ribbon icon, hotkey, or mobile
toolbar). The script will prompt you through seven steps:

| Prompt | What to enter | Example |
|--------|--------------|---------|
| Note type | One of the 9 types | `concept` |
| Subfolder | Path within the type folder (empty for root) | `information-retrieval` |
| Slug | Filename without extension | `cosine-similarity` |
| Title | Display title | `Cosine Similarity` |
| Description | One-sentence summary | `Angle-based vector similarity measure.` |
| Domain code | Short code for the ID | `IR` |
| ID number | Sequential number | `0007` |

The script creates a folder with both files and opens the `.mdx`:

```
concepts/information-retrieval/cosine-similarity/
  index.mdx           ← opens for editing
  index.meta.json     ← pre-filled template
```

After writing, add the slug to the parent folder's `meta.json` `pages` array
so it appears in the sidebar.

---

## 4. LLM context setup

The Copilot LLM is made aware of Stack Record's structure through three layers.

### Layer 1: System prompt (always active)

Go to **Settings > Copilot > Basic > System Prompt** and paste this exactly:

```
You are a Stack Record writing assistant. You help write knowledge notes
that follow a strict structure.

RULES:
- Every note is a file pair: .mdx (body, NO frontmatter) + .meta.json (sidecar)
- The .mdx must NEVER begin with --- (frontmatter). All metadata goes in .meta.json
- Required sidecar fields (build fails without): title, description, id, type
- Note types: map, concept, method, system, decision, experiment, project, standard, reference
- Status values: draft, active, evergreen, enforced, accepted, rejected, completed, superseded, archived
- Review cycles: weekly, monthly, quarterly, yearly, never
- Use [[wiki_key]] syntax (underscores) for cross-references in body text
- Sidecar array fields take wiki-style keys that resolve via key_to_note
- Always follow the exact section heading order for the note type being written
- Never reorder sections within a template
- Never use inline style={} in MDX components — all styling is CSS-only
- When suggesting [[wikilinks]], check existing vault notes first
- Every note needs at least two outward [[wiki_links]]
- Drawbacks/failure modes section must never be empty
- No note only sells the idea — be honest about limitations

SIDECAR JSON:
- All values must be valid JSON
- Array fields (related_notes, prerequisites, etc.) take string arrays
- Constrained fields use exact enum values listed above
- ID format: PREFIX-DOMAIN-NUMBER (e.g. C-IR-0007, M-RET-0012, S-CMP-0004)

When asked to help write, follow the section order for that note type exactly.
When asked to generate a .meta.json, output valid JSON with all applicable fields.
```

### Layer 2: @llm-writing-guide (on-demand full context)

A comprehensive reference note lives at `appendices/llm-writing-guide.mdx` in
the vault. To inject it as context, type in the Copilot chat:

```
@llm-writing-guide Help me write this concept note about [topic]
```

This gives the LLM the complete rulebook: all 9 body templates, all 27
connection fields, all MDX artifacts with usage guidance, closure rules, and
quality standards.

### Layer 3: Vault QA (automatic)

With Vault QA enabled, Copilot indexes all notes. The LLM can search existing
notes to suggest valid `[[wikilinks]]`, detect duplicates, and find the correct
wiki key format for existing notes.

### Example prompts

**Body writing:**
```
@llm-writing-guide I'm writing a concept note about vector similarity.
Here is my Core idea section: [paste]. Draft the Plain-English explanation
and Worked example sections.
```

**Sidecar generation:**
```
@llm-writing-guide Generate the .meta.json sidecar for this concept note.
The slug is vector-similarity, it's in the information-retrieval subfolder.
Use my vault to suggest related_notes and prerequisites.
```

**Closure check:**
```
@llm-writing-guide Review this note's .meta.json against the closure rules
for concept notes. What dimensions am I missing?
```

---

## 5. Writing workflow

### Split-pane template reference

1. Open the template file in a second pane:
   `Ctrl+Click` on `_template/example.mdx.template` in the sidebar
2. Drag the tab to the right side to create a split view
3. Write your note on the left, reference the template on the right

### Link checking

After writing, run the Broken Links command:

1. Open command palette: `Ctrl+P`
2. Type "broken links" and select the scan command
3. Review any `[[wikilinks]]` that don't resolve to existing files

### KG-builder gap analysis

For a comprehensive audit across the entire vault:

```bash
cd tools/kg-builder && docker compose run --rm kg-builder
sqlite3 data/kg.sqlite3 \
  "SELECT source_slug, target_raw, target_key
   FROM wiki_links wl
   LEFT JOIN key_to_note ktn ON ktn.key = wl.target_key
   WHERE ktn.note_id IS NULL;"
```

This finds every `[[wikilink]]` in the vault that doesn't resolve to a real
note ID. See `kg-builder-queries.md` in this folder for more queries.

---

## 6. Connection fields reference

### Edge fields by note type

| Field | Style | concept | method | system | decision | experiment | project | map | standard | reference |
|-------|-------|---------|--------|--------|----------|------------|---------|-----|----------|-----------|
| `parent_maps` | edge | x | x | x | x | x | x | | | |
| `prerequisites` | edge | x | | | | | | | | |
| `children` | edge | x | | | | | | x | | |
| `related_notes` | edge | x | x | x | x | x | x | x | x | x |
| `related_methods` | edge | x | x | x | | x | x | | | |
| `related_systems` | edge | x | x | x | | x | x | | | |
| `related_projects` | edge | x | x | x | x | x | x | | | |
| `related_experiments` | edge | x | x | x | x | | x | | | |
| `related_decisions` | edge | x | x | x | | x | x | | | |
| `related_standards` | edge | x | x | x | | | | | x | |
| `uses_concepts` | edge | | x | | | | | | | |
| `implemented_in` | edge | | x | | | | | | | |
| `validated_by` | edge | | x | | | | | | | |
| `implements_methods` | edge | | | x | | | | | | |
| `depends_on` | edge | | | x | | | | | | |
| `used_in_projects` | edge | | | x | | | | | | |
| `key_methods` | edge | | | | | | x | | | |
| `key_systems` | edge | | | | | | x | | | |
| `key_decisions` | edge | | | | | | x | | | |
| `superseded_by` | edge | x | x | x | x | x | x | x | x | x |
| `supersedes` | edge | x | x | x | x | x | x | x | x | x |
| `blocked_by` | edge | | | | | x | x | | | |
| `alternatives` | literal | | | | x | | | | | |
| `deciders` | literal | | | | x | | | | | |
| `aliases` | owned | x | x | x | | | | | | |
| `open_questions` | owned | x | x | x | x | x | x | x | x | x |
| `tags` | normalized | x | x | x | x | x | x | x | x | x |

### Closure requirements per type

| Type | U (parent map) | L (lateral >= 2) | D (child) | A (applied) | E (epistemic) | M (maintenance) |
|------|---------------|-------------------|-----------|-------------|---------------|-----------------|
| concept | `parent_maps` >= 1 | `related_notes` + `prerequisites` >= 2 | `children` >= 1 | `related_methods`/`systems`/`projects` >= 1 | `open_questions` >= 1 | `review_cycle` + `last_reviewed` set |
| method | `parent_maps` >= 1 | `related_notes` + `prerequisites` >= 2 | via `implemented_in` | `related_projects` >= 1 | `open_questions` >= 1 | `review_cycle` + `last_reviewed` set |
| system | `parent_maps` >= 1 | `related_notes` + `prerequisites` >= 2 | -- | `used_in_projects` >= 1 | `open_questions` >= 1 | `review_cycle` + `last_reviewed` set |
| decision | -- | -- | -- | `related_projects` >= 1 | `open_questions` >= 1 | `date_decided` set |
| experiment | `parent_maps` >= 1 | `related_notes` + `prerequisites` >= 2 | -- | `related_projects` >= 1 | `open_questions` >= 1 | `date_started` set |
| project | `parent_maps` >= 1 | `related_notes` >= 1 | -- | -- | `open_questions` >= 1 | `review_cycle` + `last_reviewed` set |
| map | -- | -- | `children` >= 1 | -- | `open_questions` >= 1 | `review_cycle` + `last_reviewed` set |

### ID prefix conventions

| Type | Prefix | Example |
|------|--------|---------|
| concept | `C-` | `C-IR-0007` |
| method | `M-` | `M-RET-0012` |
| system | `S-` | `S-CMP-0004` |
| decision | `D-` | `D-PUB-0001` |
| experiment | `E-` | `E-RET-0001` |
| project | `P-` | `P-UKB-0001` |
| map | `MAP-` | `MAP-LEARN-0001` |
| standard | `STD-` | `STD-CLS-0001` |
| reference | `REF-` | `REF-TPL-0001` |

---

## 7. Knowledge graph reference

The `kg-builder-queries.md` file in this folder contains the full KG builder
documentation including:

- Schema overview and table structure
- Chain traversal SQL examples (5-hop concept-to-implementation, cross-domain)
- Wiki-link gap analysis queries
- Body section search queries
- The `config/schema.yaml` control surface documentation

To run the KG builder:

```bash
cd tools/kg-builder && docker compose run --rm kg-builder
```

To query the graph:

```bash
sqlite3 tools/kg-builder/data/kg.sqlite3
```

---

## 8. Git workflow

### From Obsidian (obsidian-git plugin)

1. Command palette > "obsidian-git: Commit all changes"
2. Command palette > "obsidian-git: Push"

Or enable auto-commit/push in the plugin settings.

### From terminal

```bash
cd /path/to/stack-record
git add content-src/docs/
git commit -m "Add concept note: cosine-similarity"
git push
```

### After adding a new note, remember to

1. Add the slug to the parent folder's `meta.json` `pages` array
2. Run `pnpm docs:materialize` (or `pnpm dev`) to verify the build passes
3. Check for broken links via the Obsidian plugin or the KG builder

---

## 9. Mobile editing with Obsidian Sync

Edit notes on your phone in Obsidian with full preview, wikilinks, and Copilot
chat. Changes sync to your desktop automatically via Obsidian Sync (a paid
add-on). Git commits and pushes happen only on the desktop — the phone never
touches git directly. This workflow assumes a **solo developer**.

### How it works

```
Phone (Obsidian) ──Obsidian Sync──▸ Desktop (Obsidian) ──git──▸ GitHub
```

1. Edit on your phone in Obsidian
2. Obsidian Sync delivers changes to the desktop within seconds
3. On the desktop, review the changes, then `git add`, `git commit`, `git push`
4. Git changes never originate from the phone

Obsidian Sync and git are **two independent systems** writing to the same files
on your desktop. Because you are the only writer and you control the sequence,
the two systems never conflict — as long as you follow the workflow below.

### Pricing (Obsidian Sync, not Publish)

Obsidian Sync and Obsidian Publish are separate products. You only need **Sync**.

| | Sync Standard | Sync Plus |
|--|---------------|-----------|
| Annual billing | **$4** /user/month | **$8** /user/month |
| Monthly billing | **$5** /user/month | **$10** /user/month |
| Synced vaults | 1 | 10 |
| Total storage | 1 GB | 10 GB (upgradable to 100 GB) |
| Max file size | 5 MB | 200 MB |
| Version history | 1 month | 12 months |

Students, faculty, and nonprofit employees get **40% off**.

**Recommendation:** Sync Standard is sufficient for this project. The vault
contains only `.mdx` and `.meta.json` text files — well under 1 GB total and
5 MB per file.

### Setup: desktop (first device)

1. Create an Obsidian account at [obsidian.md/account](https://obsidian.md/account)
2. Subscribe to Sync Standard at [obsidian.md/buy/sync](https://obsidian.md/buy/sync)
3. Open Obsidian on the desktop with the vault already configured (Section 1)
4. **Settings > General**: log in with your Obsidian account
5. **Settings > Core Plugins**: enable **Sync**
6. **Settings > Sync > Remote vault > Choose > Create new vault**
   - **Name**: e.g. `stack-record`
   - **Region**: pick the server closest to you
   - **Encryption password**: set a strong password and **save it somewhere
     safe** — Obsidian cannot recover it
7. Select **Connect**, enter the encryption password
8. **Do not start syncing yet.** Configure these first:
   - **Selective sync** > **Excluded folders**: exclude any folders you do not
     want on your phone (e.g. `_template/` directories if they clutter mobile)
   - **Vault configuration sync**: enable **Core plugins**, **Community
     plugins**, **Themes**, and **Hotkeys** if you want the same editing
     environment on mobile. Leave **Workspace** off — desktop and mobile
     layouts differ.
   - **Conflict resolution**: set to **Create conflict file** (see below)
9. Restart Obsidian
10. **Settings > Sync**: select **Resume**
11. Wait for the sync icon in the status bar to turn **green** (fully synced)

### Setup: mobile (second device)

1. Install Obsidian from the [App Store](https://apps.apple.com/app/obsidian/id1557175442)
   or [Google Play](https://play.google.com/store/apps/details?id=md.obsidian)
2. Open Obsidian and create a **new empty vault** (name it e.g. `stack-record`)
3. **Settings > General**: log in with the same Obsidian account
4. **Settings > Core Plugins**: enable **Sync**
5. **Settings > Sync > Remote vault > Choose**: select the remote vault you
   created on the desktop
6. Enter the encryption password, select **Connect**
7. When prompted, **do not start syncing yet**. Configure:
   - **Selective sync**: exclude folders you do not need on mobile
   - **Vault configuration sync**: match the desktop settings above
   - **Conflict resolution**: set to **Create conflict file**
8. Restart Obsidian
9. **Settings > Sync**: select **Resume**
10. Wait for the initial download — the sync icon turns **green** when done

### The solo-dev daily workflow

1. **On phone**: open Obsidian, edit notes, close the app when finished
2. **On desktop**: open Obsidian, wait for the sync icon to turn **green**
3. **In terminal**:
   ```bash
   cd /path/to/stack-record
   git add content-src/docs/
   git commit -m "Mobile edits: [describe changes]"
   git push
   ```
4. If GitHub already has newer commits (e.g. you pushed something else from
   the terminal earlier), run `git pull` **before** opening Obsidian on the
   desktop — otherwise the pull will overwrite files that Sync is also writing

The key discipline: **always let Sync finish (green icon), then commit, before
doing anything else on the desktop.**

### Where it can go wrong

**Scenario 1 — You edit on desktop before committing phone edits**

You sit down and start editing on the desktop while Obsidian Sync is still
delivering phone changes to the same file.

- *What happens*: Sync merges markdown via diff-match-patch. It usually works,
  but can produce **duplicate text** if both edits touch the same paragraph.
- *Fix*: open the sync log (**Settings > Sync > Activity log**, filter
  **Merge Conflicts**), manually clean up duplicates, or restore from version
  history.
- *Prevention*: always wait for the green sync icon and commit phone edits
  before starting new desktop work.

**Scenario 2 — GitHub Actions modify repo files (future risk)**

This repo does not currently have CI that writes back to `content-src/docs/`.
If you add GitHub Actions that auto-format or generate files in the future:

- *What happens*: `git pull` overwrites working-tree files that Sync also just
  delivered from your phone. If both touched the same file, you get a git merge
  conflict or a silent overwrite of phone edits.
- *Fix*: `git stash` before pulling, then `git stash pop` and resolve
  conflicts manually.
- *Prevention*: always `git pull` **before** opening Obsidian on the desktop
  so that the working tree is clean when Sync starts writing.

**Scenario 3 — You commit before Sync finishes**

You run `git commit` while the sync icon is still purple.

- *What happens*: phone edits have not landed yet. They arrive later as
  uncommitted changes. `git status` shows unexpected modifications.
- *Fix*: commit the late-arriving changes in a follow-up commit.
- *Prevention*: always check that the sync icon is **green** before running
  any git command.

**Scenario 4 — You edit on phone and desktop at the same time**

Both devices modify the same file before either one syncs.

- *What happens*: Sync detects a conflict. With the recommended "Create
  conflict file" setting, it saves a copy named
  `note (Conflicted copy <device> <timestamp>).md` for manual review.
- *Fix*: compare the conflict file with the original, keep the correct
  version, delete the conflict copy.
- *Prevention*: do not edit the same note on both devices at the same time.

**Scenario 5 — Subscription expires**

- *What happens*: remote vault data is kept for **30 days** after expiry.
  Local files on both devices are untouched.
- *Fix*: resubscribe within 30 days to resume seamlessly. After 30 days the
  remote vault is deleted — create a new one and re-sync.

**Scenario 6 — Storage limit exceeded (Standard: 1 GB)**

- *Symptom*: sync stops uploading. The sync log shows "Vault limit exceeded."
- *Fix*: **Settings > Sync > Vault size over limit > View largest files**,
  delete unneeded files, then select **Prune** to reclaim remote storage.
- *Prevention*: keep the vault text-only. Exclude images and PDFs from sync,
  or upgrade to Sync Plus if you need large media files.

### Conflict resolution settings

Go to **Settings > Sync > Conflict resolution** and choose one of:

| Mode | Behaviour | Best for |
|------|-----------|----------|
| **Automatically merge** | Uses diff-match-patch for markdown; most recently modified version wins for other file types | Casual notes where occasional duplicate text is acceptable |
| **Create conflict file** | Saves a separate copy for manual review | Structured notes (like Stack Record) where duplicated sections would break templates |

**Recommended for this project: Create conflict file.** Stack Record notes
have strict section ordering — auto-merge duplicates would be harder to spot
than a conflict file you can diff and resolve.

### Troubleshooting quick reference

| Problem | Likely cause | Fix |
|---------|-------------|-----|
| Sync icon stays **red** | Not connected to remote vault | **Settings > Sync > Remote vault > Connect** |
| Sync icon stays **purple** indefinitely | Large initial sync or server issue | Check [status.obsidian.md](https://status.obsidian.md/); wait or restart Obsidian |
| "Vault not found" | Remote vault deleted or subscription lapsed > 30 days | Resubscribe, create a new remote vault |
| "Vault limit exceeded" | > 1 GB stored (Standard plan) | Delete large files via **View largest files**, then **Prune** |
| "Out of memory" on mobile | Large file being synced | Exclude that file type from sync; free device storage |
| Files keep disappearing | Another sync service (iCloud / Dropbox / OneDrive) running on the same vault folder | Move the vault out of the cloud-managed folder |
| Settings or plugins not updating on phone | Obsidian does not live-reload all settings after sync | Force-quit Obsidian on mobile and reopen |
| Git merge conflict after `git pull` | CI pushed changes while Sync delivered phone edits | `git stash`, `git pull`, `git stash pop`, resolve manually |
| Duplicate text in a note | Auto-merge conflict resolution | Switch to "Create conflict file" mode; fix the note manually |
| Conflict file appeared | Same file edited on two devices before sync | Compare both files, keep the correct version, delete the conflict copy |
| "Failed to authenticate" | Subscription expired or not logged in | Resubscribe or log in again at **Settings > General > Account** |

### Alternative: github.dev (free, no setup)

For quick single-file edits when you do not have Obsidian installed:

1. Go to your repo on GitHub in your phone's browser
2. Change `github.com` to `github.dev` in the URL (or press `.` on desktop)
3. Navigate to `content-src/docs/`
4. Edit files with VS Code in the browser
5. Use the Source Control panel to commit and push

This gives you syntax highlighting and direct commits but no Obsidian preview,
wikilink resolution, or Copilot chat.

---

## Folder structure

```
obsidian/                             ← vault root (open THIS in Obsidian)
├── .obsidian/                        ← Obsidian config (gitignored)
├── scripts/                          ← Templater scripts
│   ├── create-note-pair.js
│   └── _new-note.md
├── copilot/                          ← Copilot plugin data
│   └── copilot-custom-prompts/       ← shared prompt templates
├── README.md                         ← this file
├── kg-builder-queries.md             ← SQL query reference for the KG
├── appendices -> ../content-src/docs/appendices
├── concepts -> ../content-src/docs/concepts
├── decisions -> ../content-src/docs/decisions
├── experiments -> ../content-src/docs/experiments
├── maps -> ../content-src/docs/maps
├── methods -> ../content-src/docs/methods
├── notes -> ../content-src/docs/notes
├── projects -> ../content-src/docs/projects
├── standards -> ../content-src/docs/standards
└── systems -> ../content-src/docs/systems

content-src/docs/                     ← documentation source (clean)
├── appendices/
├── concepts/
├── methods/
├── ...
├── index.mdx
├── index.meta.json
└── meta.json
```

The content folders in `obsidian/` are symlinks tracked in git. Cloning the
repo recreates them automatically on Linux/macOS. Edits made through Obsidian
write directly to `content-src/docs/` — git sees changes there, not in
`obsidian/`. VS Code/Cursor shows an arrow overlay on symlinked folders to
distinguish them from real folders.
