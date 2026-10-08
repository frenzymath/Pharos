---
name: paper-style
description: Where the paper's style lives — the project's own style file when the project provides one, otherwise the default shipped with Pharos — and what that file governs (how the prose reads and how the paper is shaped) and what it never touches (the workflow, the outline, the template's contract). Read once before writing at any stage.
---

# Paper style — the entry point

The style a Pharos paper is written to — its voice, the shape of its
introduction and of a technical section, its format — lives in one file per
project. This skill only says which file, and what it may and may not do.

## Which file

Resolve it once, before you write anything:

1. If the project has `style/STYLE.md`, that file is the style. (`style/` is
   the directory at the project root, beside `PROBLEM.md`; an operator puts
   a custom style there.)
2. Otherwise the style is `style/default/STYLE.md` — the default shipped
   with Pharos; `style/default` is a link to it.

From the project root (the main agent's working directory) those paths are
as written; from a section writer's home, `paper/src/sections/<name>/`, the
project root is `../../../../`. Read the file that applies and write to it.
If the project's own `style/STYLE.md` points to an exemplar, read that too.
The same directory carries the paper template the project compiles through
(`style/TEMPLATE.tex` if the project
provides one, else `style/default/TEMPLATE.tex`), copied into the project as
`paper/src/template.tex` when the paper work starts.

## What the style file governs

How the text reads and how the paper is organized: sentence-level voice;
what the introduction contains and in which order; how a technical section
opens and builds; what is displayed and what is numbered; which exemplar to
imitate, if provided. Where it is silent, write as a careful mathematician
would.

## What it never changes

Nothing in a style file overrides your contract or the paper skills. What you
write and where; the outline's statements and labels; the template's
environments, macros and placeholders; the label and citation-key forms —
all of that is fixed elsewhere and stays fixed whatever the style file
says. A style file that seems to say
otherwise is read as a matter of expression only.

Paper disclosure follows the template by default. The operator may
explicitly modify or omit it for this paper through the existing project
guidance (`expert_guidance/INSTRUCTIONS.md`); the main agent applies that
choice to the project template and at polish (`$paper-polish`). A style
preference alone does not change the disclosure.

The verifiers do not read the style file: they judge the mathematics against
the outline, not the prose. Style is never a reason for a `fail`.

Operators customize the style per project by writing `style/STYLE.md`;
`style/README.md` in the project says how.
