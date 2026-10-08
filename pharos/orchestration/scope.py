"""CLI scope based on the working directory.

Outside projects, OPS permits deployment commands with explicit targets.
A project root selects MAIN and pins commands to that project. Descendant
directories have NONE scope; only ``ANY_SCOPE`` commands are available there.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional, Tuple

OPS = "ops"
MAIN = "main"
NONE = "none"

#: Verbs that act on the whole deployment — only from outside a project.
OPS_ONLY = frozenset({"new", "list", "main", "doctor"})

#: Commands available in agent homes. Compute checks its script's project itself.
ANY_SCOPE = frozenset({"compute", "usage", "render"})


def current(cwd: Optional[Path] = None) -> Tuple[str, Optional[str]]:
    """``(scope, project)`` for the working directory.

    Recognize projects by ``project.json`` and ``workers/`` so relocated
    projects retain their scope.
    """
    here = (cwd or Path.cwd()).resolve()
    for candidate in (here, *here.parents):
        if (candidate / "project.json").is_file() and (candidate / "workers").is_dir():
            return (MAIN if candidate == here else NONE), candidate.name
    return OPS, None


def check(verb: str, cwd: Optional[Path] = None) -> Tuple[str, Optional[str]]:
    """Authorize ``verb`` here, or exit with an explanation. Returns the scope."""
    scope, project = current(cwd)
    if verb in ANY_SCOPE:
        return scope, project
    if scope == OPS:
        return scope, project
    if scope == NONE:
        raise SystemExit(
            f"`pharos {verb}` is not available here.\n"
            f"  This directory belongs to project {project!r} but is not its root: a "
            f"worker or subagent home only permits compute, usage, and render. "
            f"Use your role's tools and files for other work."
        )
    if verb in OPS_ONLY:
        raise SystemExit(
            f"`pharos {verb}` runs the deployment, not one project — it is the ops "
            f"agent's, from the Pharos root directory.\n"
            f"  You are the main agent of {project!r}; ask the operator if the "
            f"deployment needs something."
        )
    return scope, project


def pin(target: Optional[str], scope: str, project: Optional[str], *,
        verb: str, need_worker: bool = False) -> str:
    """Resolve a verb's target under the current scope.

    Under OPS the target is required and passed through. Under MAIN the project
    is implicit: ``None`` means this project, a bare name means a worker of it,
    and naming a different project is refused."""
    if scope == OPS:
        if not target:
            raise SystemExit(f"`pharos {verb}` needs a target: <project>"
                             + ("/<worker>" if need_worker else "[/<worker>]"))
        return target
    if not target:
        if need_worker:
            raise SystemExit(f"`pharos {verb}` needs a worker: `pharos {verb} <worker> …`")
        return project or ""
    named, _, rest = target.partition("/")
    if named == project:
        return target
    if rest:
        raise SystemExit(
            f"`pharos {verb} {target}` names project {named!r}, but this directory is "
            f"project {project!r}. A main agent acts only on its own project."
        )
    return f"{project}/{target}"
