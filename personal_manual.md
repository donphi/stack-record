# Personal Manual Steps — Public Repo Setup

These are the steps YOU do manually. They involve git commands that require your
decisions. Do them in order.

After completing these steps, the automated cleanup (file deletions, identity
scrubbing, reference removal) can be run on the `public` branch by the agent.

---

## Current state (already done)

- [x] GitHub: stack-record (public) exists at `upstream`
- [x] GitHub: stack-record-private (private) exists at `origin`
- [x] Remotes configured: `origin` → private, `upstream` → public
- [x] `main` branch tracks `origin/main`

Verify anytime:

```bash
git remote -v
# origin    git@github.com:donphi/stack-record-private.git
# upstream  git@github.com:donphi/stack-record.git
```

---

## Step 1 — Commit everything and push to private

You have ~204 uncommitted changes (the folder restructure, new content, and new
files like git_opensource.md and this file). Commit and push them all to your
private repo:

```bash
git add .
git commit -m "feat: restructure content-src into folder groups, add git guide and workflow docs"
git push origin main
```

Everything — all personal content, all history — is now safely backed up in your
private repo. This is your safety net.

---

## Step 2 — Create the public branch

```bash
git checkout -b public main
```

You are now on the `public` branch. This is an exact copy of `main` right now.
The automated cleanup will strip personal content from THIS branch only. Your
`main` branch stays untouched.

---

## Step 3 — Run the automated cleanup

Tell the agent to execute the cleanup plan. It will (on the `public` branch
only):

- Delete personal content folders (projects, experiments, decisions, inbox,
  git-guide, personal obsidian docs, libs.md, git_opensource.md,
  personal_manual.md)
- Empty the `pages` arrays in meta.json files for stripped sections
- Replace "Donald Philp" with "Your Name" in templates
- Replace the GitHub URL in layout.shared.tsx with a placeholder
- Remove ukb_pipeline/batch_orchestrator/gatehouse references from ~42 files
- Add sqlite3 and sync.log to .gitignore

---

## Step 4 — Review the public branch

Before pushing, verify what the public repo will look like:

```bash
# See what's different from main (your private content)
git diff --name-status public..main

# Search for any remaining personal data
git grep -i "donald\|donphi"

# Visual tree (if diffnav is installed)
git diff public..main | diffnav
```

Check that:
- [ ] No personal project folders exist (ukb-pipeline, gatehouse, etc.)
- [ ] No experiment/decision content exists
- [ ] No git-guide folder exists
- [ ] No "Donald Philp" or "donphi" in any file
- [ ] No inbox/notes content exists
- [ ] No git_opensource.md or personal_manual.md
- [ ] Templates and _template folders still exist
- [ ] Standards and appendices (minus git-guide) still exist
- [ ] All concepts, methods, systems content still exists
- [ ] Framework code (app/, lib/, scripts/, components/) is intact

---

## Step 5 — Push the public branch

```bash
git push upstream public:main
```

This pushes your local `public` branch as `main` on the public repo. The public
GitHub repo now has the clean, framework-only version.

---

## Step 6 — Go back to your daily branch

```bash
git checkout main
```

You're back on your working branch with all personal content intact.

---

## Step 7 — Install diffnav (optional but recommended)

```bash
brew install dlvhdr/formulae/diffnav
```

Or from source (needs Go 1.21+):

```bash
git clone https://github.com/dlvhdr/diffnav.git
cd diffnav && go install .
```

Install a Nerd Font for icons:

```bash
brew install --cask font-commit-mono-nerd-font
```

Set up the git alias:

```bash
git config alias.private-diff '!git diff public..main | diffnav'
```

Now `git private-diff` shows you the colored tree anytime.

---

## Step 8 — Daily habits going forward

```bash
# Daily: push everything to private
git push origin main

# When you do framework work: cherry-pick to public
git checkout public
git cherry-pick <hash>
git push upstream public:main
git checkout main

# Weekly/monthly: pull any community contributions
git fetch upstream
git checkout main
git merge upstream/main
git push origin main
```

See `git_opensource.md` for the full reference with diffnav usage, partial
cherry-picks, common mistakes, and a quick-reference table.
