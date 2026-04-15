# notes/

This is the **inbox** -- scratch notes, ideas, and unprocessed thoughts that have not yet been promoted to a proper note type.

## Page structure (MDX body)

No strict heading template. Write freely. The `.mdx` file must **not** contain YAML frontmatter.

When an idea matures, move it to the correct section (concepts/, methods/, etc.) and give it the proper type-specific sidecar and body template.

## JSON sidecar structure (*.meta.json)

**Required fields (build will fail without these):**

| Field | Type | Example |
|-------|------|---------|
| `title` | string | `"Ideas"` |
| `description` | string | `"Raw ideas and future investigation topics."` |
| `id` | string | `"NOTE-IDEAS-0001"` |
| `type` | string | Any valid type (often `"map"` for the index) |

Notes in the inbox have minimal metadata requirements. The goal is low friction -- capture the idea, worry about structure later.

## Folder navigation (meta.json)

```json
{
  "title": "Notes",
  "icon": "EditPencil",
  "pages": ["index", "ideas"]
}
```

## Promoting a note

When a note is ready to become a real concept/method/system/etc.:

1. Choose the target type and folder
2. Copy the `_template/` files from the target folder
3. Migrate the content into the template structure
4. Set the correct `type` in the sidecar
5. Fill in all mandatory connection fields
6. Add the slug to the target folder's `meta.json`
7. Remove the old note from `notes/meta.json`
8. Run `docker compose up --build` to rebuild and verify
