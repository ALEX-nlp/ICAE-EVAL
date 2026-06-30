"""Render the agent-under-test task prompt from prompt_templates/task_docker.md.

Unlike the original task_3.md (which hands the agent a tar to load), this gives
the agent a *running container id* and tells it to develop via `docker exec`.
"""
from . import config as C
from .docker_env import WORKDIR, PRD_NAME


def render_task_prompt(alias: str, *, docker_id: str, lang: str) -> str:
    template = C.TASK_TEMPLATE.read_text(encoding="utf-8")
    return template.format(
        docker_id=docker_id,
        workdir=WORKDIR,
        prd_name=PRD_NAME,
        lang=lang or "(unspecified)",
    )
