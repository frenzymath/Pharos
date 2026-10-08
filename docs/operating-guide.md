# Operating guide

## Give the project a problem and materials

Start with the operations session in the repository root. Describe the question,
point it to papers or notes, and give any directions about approaches or sources.
Ops prepares a project and shows you `PROBLEM.md` and the initial guidance for
confirmation before it starts the research team.

| Project path | Purpose |
| --- | --- |
| `PROBLEM.md` | The agreed research question |
| `materials/` | Supplied papers, notes, and other context |
| `expert_guidance/INSTRUCTIONS.md` | Your research instructions, recorded verbatim |
| `expert_guidance/GUIDANCE.md` | Their current digest and source restrictions |
| `literature/` | The survey, papers, and reading notes gathered during research |

Materials and guidance provide context; mathematical claims still pass through
the verification process before becoming facts.

## Work with the main agent

The root ops session handles setup and can inspect several projects. Each
project's main session handles its research: it surveys prior work, organizes
routes on `ROUTES.md`, briefs workers, and reviews their results. Workers can
stay with a substantial question across rounds; an unfinished proof remains
in their working memory until they can submit a result.

Give new research directions to the main session, where they enter the guidance
record. Ask it to explain a route's evidence, its obstruction, or why it assigned
particular work. The [architecture guide](architecture.md) explains how the
live route board and dated checkpoints preserve these decisions.

For a separate discussion, use `pharos chat <project>`. That conversation does
not automatically become a research instruction; carry any decision to the
main session yourself.

## Read progress and prepare a paper

Ask ops which projects are running, or request a report for a named project.
`pharos report <project>` produces a Markdown report and PDF in `human_report/`;
it reads the latest checkpoint and retrieves the facts cited in the report.
The route board and checkpoints remain available for a more detailed account.

When a target is established, discuss the result with the main agent and ask
it to prepare a paper. It coordinates the outline, section writers, section
verification, and whole-paper review; PDFs are built under `paper/`.
You can supply a project `style/STYLE.md`, `style/TEMPLATE.tex`, or an optional
exemplar; the generated `style/README.md` explains their use.

System disclosure and acknowledgements are included by default. Give the main
agent any paper-specific changes or omissions, keeping statements about
contributions and verification faithful to the actual work. See the
[style resources](../agents/resources/default-style/README.md).

For a pause or complete stop, specify the project to ops and use the scope
explained in [Operations](operations.md#stop-and-recover).
