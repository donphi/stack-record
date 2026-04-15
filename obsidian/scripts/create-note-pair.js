/**
 * Templater user script: create a paired .mdx + .meta.json from templates.
 *
 * Invoked via:  <%* await tp.user["create-note-pair"](tp) %>
 *
 * Prompts for note type, subfolder, slug, title, and description,
 * then reads the correct _template/ files, performs variable substitution,
 * creates both files, and opens the .mdx for editing.
 */

const NOTE_TYPES = {
  concept:    { folder: "concepts",     idPrefix: "C",   defaultReview: "monthly"    },
  method:     { folder: "methods",      idPrefix: "M",   defaultReview: "monthly"    },
  system:     { folder: "systems",      idPrefix: "S",   defaultReview: "quarterly"  },
  decision:   { folder: "decisions",    idPrefix: "D",   defaultReview: "yearly"     },
  experiment: { folder: "experiments",  idPrefix: "E",   defaultReview: "never"      },
  project:    { folder: "projects",     idPrefix: "P",   defaultReview: "monthly"    },
  map:        { folder: "maps",         idPrefix: "MAP", defaultReview: "quarterly"  },
  standard:   { folder: "standards",    idPrefix: "STD", defaultReview: "yearly"     },
  reference:  { folder: "appendices",   idPrefix: "REF", defaultReview: "yearly"     },
};

async function createNotePair(tp) {
  const noteType = await tp.system.suggester(
    Object.keys(NOTE_TYPES),
    Object.keys(NOTE_TYPES),
    false,
    "Note type"
  );
  if (!noteType) return;

  const config = NOTE_TYPES[noteType];

  const subfolder = await tp.system.prompt(
    `Subfolder within ${config.folder}/ (leave empty for root)`,
    "",
    false
  );

  const slug = await tp.system.prompt("Slug (e.g. cosine-similarity)", "", false);
  if (!slug) { new Notice("Slug is required"); return; }

  const title = await tp.system.prompt("Title", "", false);
  if (!title) { new Notice("Title is required"); return; }

  const description = await tp.system.prompt("Description (one sentence)", "", false);
  if (!description) { new Notice("Description is required"); return; }

  const domainCode = await tp.system.prompt(
    `Domain code for ID (e.g. IR, RET, CMP)`,
    subfolder ? subfolder.toUpperCase().replace(/-/g, "").slice(0, 4) : noteType.toUpperCase().slice(0, 4),
    false
  );

  const idNumber = await tp.system.prompt("ID number (e.g. 0001)", "0001", false);

  const targetDir = subfolder
    ? `${config.folder}/${subfolder}`
    : config.folder;

  const slugDir  = `${targetDir}/${slug}`;
  const mdxPath  = `${slugDir}/index.mdx`;
  const jsonPath = `${slugDir}/index.meta.json`;

  if (await app.vault.adapter.exists(slugDir)) {
    new Notice(`Folder already exists: ${slugDir}`);
    return;
  }

  const templateDir = `${config.folder}/_template`;
  const mdxTemplatePath  = `${templateDir}/example.mdx.template`;
  const jsonTemplatePath = `${templateDir}/example.meta.json.template`;

  let mdxTemplate, jsonTemplate;
  try {
    const mdxFile = app.vault.getAbstractFileByPath(mdxTemplatePath);
    const jsonFile = app.vault.getAbstractFileByPath(jsonTemplatePath);
    if (!mdxFile || !jsonFile) throw new Error("Template files not found");
    mdxTemplate = await app.vault.read(mdxFile);
    jsonTemplate = await app.vault.read(jsonFile);
  } catch (e) {
    new Notice(`Cannot read templates from ${templateDir}/: ${e.message}`);
    return;
  }

  const today = tp.date.now("YYYY-MM-DD");
  const noteId = `${config.idPrefix}-${domainCode}-${idNumber}`;
  const tagPrefix = `${noteType}/${domainCode.toLowerCase()}`;

  const jsonContent = jsonTemplate
    .replace(/\{\{DOMAIN\}\}/g, domainCode)
    .replace(/\{\{CODE\}\}/g, domainCode)
    .replace(/\{\{NUMBER\}\}/g, idNumber)
    .replace(/\{\{TAG\}\}/g, domainCode.toLowerCase())
    .replace(/"title":\s*""/, `"title": "${title.replace(/"/g, '\\"')}"`)
    .replace(/"description":\s*""/, `"description": "${description.replace(/"/g, '\\"')}"`)
    .replace(/"id":\s*"[^"]*"/, `"id": "${noteId}"`)
    .replace(/"last_reviewed":\s*""/, `"last_reviewed": "${today}"`);

  if (!(await app.vault.adapter.exists(targetDir))) {
    await app.vault.createFolder(targetDir);
  }
  await app.vault.createFolder(slugDir);

  await app.vault.create(mdxPath, mdxTemplate);
  await app.vault.create(jsonPath, jsonContent);

  const createdFile = app.vault.getAbstractFileByPath(mdxPath);
  if (createdFile) {
    await app.workspace.getLeaf(false).openFile(createdFile);
  }

  new Notice(`Created ${slug}/index.mdx + index.meta.json in ${targetDir}/`);
}

module.exports = createNotePair;
