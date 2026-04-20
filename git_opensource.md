# Open-Source Workflow Reference

This file is private. It lives on your working branch and is never cherry-picked
to the `public` branch. It documents how the two-repo, two-remote separation
works so you never have to think from scratch.

---

## 1 — Where the separation physically happens

There is no config file, no `.gitignore` rule, no UI toggle, and no automated
filter that decides what is public and what is private.

The entire mechanism is two things:

1. **Which branch a commit lives on.**
2. **Which remote you push that branch to.**

That's it. If a commit is on `main` and you push `main` to `origin`, it goes to
your private repo. If a commit is on `public` and you push `public` to
`upstream`, it goes to the public repo. Nothing else controls visibility.

---

## 2 — Remotes and branches

```
REMOTES
  origin   → stack-record-private  (GitHub, private)  ← daily push
  upstream → stack-record           (GitHub, public)   ← clean framework only

BRANCHES
  main     → your daily work, all content, pushed to origin only
  public   → curated clean version, pushed to upstream only
```

Verify anytime:

```bash
git remote -v
git branch -vv
```

---

## 3 — Forking a framework feature to public

You fixed a bug in the materialiser, improved a component, updated a template,
or added a standard. This is generic work that belongs in the public repo.

```bash
# 1. Find the commit hash on your working branch
git log --oneline -10

# 2. Switch to the clean branch
git checkout public

# 3. Cherry-pick the commit — THIS is the selection moment
git cherry-pick <hash>

# 4. Push to the public repo
git push upstream public:main

# 5. Go back to your daily branch
git checkout main
```

If the commit touches both framework and personal files, do NOT cherry-pick it
directly. Instead:

```bash
git checkout public
git cherry-pick --no-commit <hash>
# Unstage the personal files
git restore --staged content-src/docs/(03-operations)/...
git restore content-src/docs/(03-operations)/...
# Commit only the framework parts
git commit -m "fix: materialiser handles empty sidecars"
git push upstream public:main
git checkout main
```

### Multiple commits at once

```bash
git checkout public
git cherry-pick <hash1> <hash2> <hash3>
git push upstream public:main
git checkout main
```

---

## 4 — Keeping personal content personal

When you write a new concept note, add an experiment, update a project page, or
edit your git-guide — do nothing special. Just work on `main` and push to
`origin`:

```bash
git add .
git commit -m "docs: add transformer attention concept note"
git push origin main
```

It stays private because you never cherry-pick it to `public` and you never push
`main` to `upstream`. That's the whole mechanism.

---

## 5 — Pulling community contributions

Someone opens a PR on the public repo and it gets merged. Bring those changes
into your working branch:

```bash
git fetch upstream
git checkout main
git merge upstream/main
git push origin main
```

If there are conflicts (unlikely unless you modified the same framework file
differently on both sides):

```bash
# Resolve conflicts in your editor, then:
git add .
git commit
git push origin main
```

---

## 6 — Seeing what's private vs public

### Quick text list

```bash
git diff --name-status public..main
```

Output: `A` = private-only, `D` = public-only, `M` = different between them.

### Interactive colored tree with diffnav

diffnav gives you a GitHub-style file tree sidebar in the terminal, color-coded
by status. This is the best way to see the full private-vs-public picture at a
glance.

#### Install

Homebrew (macOS/Linux):

```bash
brew install dlvhdr/formulae/diffnav
```

From source (needs Go 1.21+):

```bash
git clone https://github.com/dlvhdr/diffnav.git
cd diffnav
go install .
```

Nerd Font (required for icons to render):

```bash
brew install --cask font-commit-mono-nerd-font
```

Then set that font as your terminal font in your terminal emulator's settings.

#### Usage

```bash
# One-shot: see private-vs-public tree right now
git diff public..main | diffnav

# Watch mode: live-updating as you work
diffnav --watch-cmd "git diff public..main"
```

What you see:
- Left pane: collapsible file tree, color-coded (green = private-only,
  red = public-only, yellow = modified between branches).
- Right pane: the actual diff for the selected file.

#### Keyboard shortcuts

| Key      | Action                          |
|----------|---------------------------------|
| `j` / `k` | Move up/down in file tree     |
| `n` / `p` | Jump to next/previous file    |
| `e`      | Toggle file tree sidebar        |
| `s`      | Toggle side-by-side / unified   |
| `Tab`    | Switch focus between panes      |
| `o`      | Open file in $EDITOR            |
| `y`      | Copy file path                  |
| `q`      | Quit                            |

#### Git alias for quick access

```bash
git config alias.private-diff '!git diff public..main | diffnav'
```

Then just:

```bash
git private-diff
```

#### Optional config

Create `~/.config/diffnav/config.yml`:

```yaml
ui:
  fileTreeWidth: 40
  icons: nerd-fonts-full
  colorFileNames: true
  showDiffStats: true
  sideBySide: true
```

---

## 7 — Common mistakes

**Accidentally pushing main to upstream.**
Always check the remote before pushing. The alias `git private-diff` is a good
pre-push habit — if you see personal files about to go upstream, stop.

```bash
# Safe: explicit remote and branch
git push origin main
git push upstream public:main

# Dangerous: if upstream is set as default push target
git push
```

**Cherry-picking a commit that references personal content.**
If your commit message mentions `ukb-pipeline` or a commit touches a personal
file alongside a framework file, use `cherry-pick --no-commit` and selectively
stage only the framework changes (see section 3).

**Forgetting to sync the public branch.**
When you do framework work, cherry-pick promptly. Letting the public branch
drift far behind makes cherry-picks harder due to conflicts.

**Force-pushing to upstream.**
Never, unless you are the sole user and you coordinate. Use `--force-with-lease`
if you absolutely must.

---

## 8 — Quick reference

| I want to...                          | Command                                          |
|---------------------------------------|--------------------------------------------------|
| Push daily work (private)             | `git push origin main`                           |
| Send a framework fix to public        | `git checkout public && git cherry-pick <hash> && git push upstream public:main && git checkout main` |
| Pull community contributions          | `git fetch upstream && git merge upstream/main`   |
| See what's private vs public (text)   | `git diff --name-status public..main`            |
| See what's private vs public (visual) | `git diff public..main \| diffnav`               |
| See what's private vs public (live)   | `diffnav --watch-cmd "git diff public..main"`    |
| Check which remote is which           | `git remote -v`                                  |
| Check branch tracking                 | `git branch -vv`                                 |
