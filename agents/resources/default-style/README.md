# The paper style of this project

This directory, `style/` at the project root beside `PROBLEM.md`, holds the
style the paper of this project is written to. It contains `README.md`
(this file); `default/`, a link to the default style package shipped with
Pharos (`agents/resources/default-style/` in the Pharos checkout: `STYLE.md`,
`TEMPLATE.tex`, `README.md`); and, optionally, your own `STYLE.md`,
`TEMPLATE.tex`, and `exemplar/`.

## How the style is chosen

- The style file is `STYLE.md` here if it exists, otherwise
  `default/STYLE.md`.
- The template is `TEMPLATE.tex` here if it exists, otherwise
  `default/TEMPLATE.tex`. It is copied to `paper/src/template.tex` when the
  paper work starts (the first `pharos paper assign`); from then on the
  project's copy is what the build compiles, and the file here is not read
  again. A template of your own has to be in place before then.
- An `exemplar/` of your own may sit here; point to it from your `STYLE.md`.

## Writing a custom STYLE.md

Start from the default:

    cp default/STYLE.md STYLE.md

Keep the YAML header — a `name:` line and a one-line `description:` — and
write the rest in English. Describe how the prose reads and how the paper is
organized: the voice, the parts of the introduction and their order, how a
technical section opens and builds, what is displayed and what is numbered,
which exemplar to imitate, if you provide one. Write it as description, not
as instructions to anyone in particular. The copied file names `TEMPLATE.tex`
beside it; make that `default/TEMPLATE.tex`, or provide your own.

## What a style file cannot do

A style file governs expression only. It does not change the workflow (the
stages, who writes what and where); the outline's statements and their
labels; the template's environments, macros and placeholders; the forms of
labels and citation keys.

A template of your own keeps the two placeholders `%%TITLE%%` and
`%%SECTIONS%%` (the second exactly once, on its own line, not in a comment),
and the template's set of theorem environments. Fonts, margins, colors, the
author block are yours to change.

## Paper disclosure

The default includes the abstract's system disclosure, the system and team
acknowledgements, the Rethlas reference, and the appendix on generative AI.
Keep them unless the operator explicitly changes or omits them for this
paper, including when supplying a custom template. Record that choice in
the existing `expert_guidance/INSTRUCTIONS.md`; the main agent applies it to
`paper/src/template.tex` and, at polish, the introduction's acknowledgements.

Describe contributions, funding and verification only as supported by the
operator's information and the project's records; do not invent them.
Removing disclosure does not remove mathematical support: preserve any
computation details needed to reproduce a result, and update appendix
references and bibliography entries to match the text that remains.

## Who reads it

The main agent, when it plans the paper and writes the outline, and again
when it polishes; every section writer. The verifiers do not read it: they
judge the mathematics against the outline, and style is never a reason for
a failed verdict.

## Changing the default

`default/` is a link into the Pharos checkout: editing the package there
changes the default for every project; files here change this project only.
