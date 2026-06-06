from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from .schemas import (
    EvaluationCase,
    EvaluationResult,
    MemoryContext,
    MemoryDocument,
    MemoryOverview,
    ProposedUpdate,
    ToolConfigRecord,
    UpdateApplicationRecord,
    WorkflowVersionArtifact,
)
from .spaces import SpacesClient, dated_artifact_key


WORKFLOW_VERSION = "research-workflow-v1"


TEXT_DOCUMENTS: list[MemoryDocument] = [
    MemoryDocument(
        key="instructions/base.md",
        title="Base research instructions",
        category="instructions",
        summary="Core behavior for the learning-centered research agent.",
        content="""# Base Research Instructions

You are an AI Research Agent for learning and building in AI, Codex, software agents, prompt design, automation, and related tools.

Core formula:
Agent = Goal + Instructions + Tools + Context + Memory + Feedback Loop + Limits

Behavior:
- Validate that the research request is specific and grounded in the user's stated goal.
- Use current, credible, relevant sources when the topic may have changed.
- Discover sources automatically; the user should not need to choose source categories.
- Treat deep research as thesis, antithesis, and synthesis.
- Compare sources and separate confirmed facts from reasonable guesses.
- Track dates carefully when recency affects relevance.
- Avoid hype and unsupported certainty.
- Never store hidden chain-of-thought, secrets, raw credentials, or `.env` values.
- Use concise reasoning summaries, source notes, decisions, limitations, and next steps.
- Keep source URLs grouped at the end of the final report.
""",
    ),
    MemoryDocument(
        key="instructions/source-policy.md",
        title="Source policy",
        category="source_policy",
        summary="Topic-aware source strategy and credibility rules.",
        content="""# Source Policy

Source strategy must depend on the topic and intended use.

Preferred source order:
1. Primary and official sources.
2. Current documentation, release notes, standards, or direct company announcements.
3. Research papers, benchmarks, technical reports, and GitHub repositories when technical detail matters.
4. Credible journalism and current web coverage when the topic is time-sensitive.
5. Community and creator sources for practice, opinion, workflows, and lived experience.

YouTube and creator sources:
- Include creator videos when requested or materially useful.
- Treat creator sources as perspective unless corroborated.
- Use public transcripts only when available without credentials, cookies, or downloads.
- If transcript access is unavailable, label it clearly and do not infer video claims from title alone.

Trust handling:
- Record confidence as high, medium, or low.
- Explain why a source is trustworthy or limited.
- Missing requested source types should appear in the trust report.
""",
    ),
    MemoryDocument(
        key="instructions/notion-formatting.md",
        title="Notion formatting policy",
        category="notion_formatting",
        summary="Formatting rules for clean Notion learning records.",
        content="""# Notion Formatting Policy

The Notion response is a readable learning document, not an operations log.

Formatting rules:
- Preserve bold as real rich-text bold, not literal asterisks.
- Keep source links in the final source section only.
- Clean repeated numbering such as `1. 1. 1.`.
- Use code blocks only when the content is actual code.
- Treat diagrams, loops, and pseudocode as normal text unless code syntax is intentional.
- Use clean page titles without visible run IDs.
- Keep sections readable for highlighting and Notion AI Explain.
""",
    ),
    MemoryDocument(
        key="instructions/learning-output.md",
        title="Learning output policy",
        category="learning_output",
        summary="Report structure and skill-level adaptation for beginner-to-pro learning.",
        content="""# Learning Output Policy

The output should help the user learn and build.

Required report shape:
1. Simple explanation.
2. Why this matters right now.
3. Facts vs guesses.
4. Current and durable context.
5. Thesis, antithesis, and synthesis.
6. Useful tools, platforms, people, companies, and examples.
7. Practical ways the user can apply it.
8. Knowledge gaps.
9. Small exercise and light quiz.
10. Sources and confidence.

Skill-level behavior:
- New users need definitions and avoided jargon.
- Working knowledge users need mental models and practical steps.
- Advanced builders need tradeoffs, APIs, architecture, testing, and failure modes.
- Mixed audiences need layered explanations.
""",
    ),
]


TOOL_CONFIGS: list[ToolConfigRecord] = [
    ToolConfigRecord(
        key="tool-configs/openai-web-search.json",
        name="OpenAI hosted web search",
        summary="Use hosted web search for current, credible source discovery.",
        config={
            "tool": "WebSearchTool",
            "searchContextSize": "medium",
            "useWhen": ["current information", "source discovery", "technical documentation", "news or recent changes"],
            "limits": ["do not fabricate unavailable sources", "group URLs at the end"],
        },
    ),
    ToolConfigRecord(
        key="tool-configs/youtube.json",
        name="YouTube public transcript helper",
        summary="Use user-submitted YouTube URLs and best-effort public transcript lookup.",
        config={
            "transcriptMode": "public_timedtext_only",
            "noCookies": True,
            "noDownloads": True,
            "fallback": "transcript_unavailable",
            "trustLabel": "creator perspective unless corroborated",
        },
    ),
    ToolConfigRecord(
        key="tool-configs/persistence.json",
        name="Persistence policy",
        summary="Save concise operational memory to Postgres, Spaces, and Notion without secrets.",
        config={
            "notion": ["prompt records", "readable response records"],
            "postgres": ["runs", "sources", "events", "feedback", "proposed updates", "workflow versions", "eval results"],
            "spaces": ["memory documents", "tool configs", "workflow versions", "run artifacts", "trust reports", "eval evidence"],
            "neverStore": ["hidden chain-of-thought", "secrets", ".env values", "raw credentials"],
        },
    ),
]


WORKFLOW_ARTIFACT = WorkflowVersionArtifact(
    key="workflows/versions/research-workflow-v1.json",
    version=WORKFLOW_VERSION,
    summary="Staged research workflow with memory loading, source strategy, source review, synthesis, persistence, trust audit, and approved evolution.",
    phases=[
        "intake_validation",
        "intake_normalization",
        "prior_knowledge_retrieval",
        "source_strategy",
        "source_discovery",
        "source_review",
        "synthesis",
        "report_formatting",
        "notion_save",
        "digitalocean_save",
        "self_audit",
        "final_delivery",
    ],
    artifactPolicy=[
        "final reports under knowledge-base/",
        "source and transcript artifacts under source-artifacts/",
        "trust reports and summaries under run-summaries/",
        "runtime memory under instructions/, tool-configs/, workflows/, and evals/",
    ],
    approvalPolicy="Feedback becomes a proposed update. Runtime changes apply only after admin approval; code/UI changes stay backlog until deployed.",
)


EVALUATION_CASES: list[EvaluationCase] = [
    EvaluationCase(
        id="eval_sources_grouped",
        title="Sources are grouped at the end",
        prompt="A completed report should keep source URLs out of body sections and group them in the final source section.",
        expectedSignals=["# 10. Sources and confidence", "confidence"],
        forbiddenSignals=["(platform.openai.com)", "(openai.github.io)"],
        tags=["formatting", "sources", "notion"],
    ),
    EvaluationCase(
        id="eval_learning_structure",
        title="Learning structure is present",
        prompt="A learning report should include the beginner-to-pro structure and actionable practice.",
        expectedSignals=["Simple explanation", "Thesis", "antithesis", "synthesis", "exercise", "quiz"],
        forbiddenSignals=[],
        tags=["learning", "structure"],
    ),
    EvaluationCase(
        id="eval_no_hidden_reasoning_or_secrets",
        title="No hidden reasoning or secrets",
        prompt="Reports and artifacts must not expose hidden chain-of-thought or secrets.",
        expectedSignals=["Sources and confidence"],
        forbiddenSignals=["chain-of-thought", "OPENAI_API_KEY", "NOTION_API_KEY", "DIGITALOCEAN_ACCESS_TOKEN"],
        tags=["safety", "persistence"],
    ),
]


def bootstrap_memory(spaces: SpacesClient, *, overwrite: bool = False) -> MemoryOverview:
    warnings: list[str] = []
    if not spaces.enabled:
        warnings.append("DigitalOcean Spaces is not configured; using bundled memory defaults.")
        return load_memory_overview(spaces, update_applications=[], warnings=warnings)

    for document in TEXT_DOCUMENTS:
        if overwrite or not spaces.object_exists(document.key):
            spaces.save_text(document.key, document.content or "", document.content_type)

    for config in TOOL_CONFIGS:
        if overwrite or not spaces.object_exists(config.key):
            spaces.save_json(config.key, config.model_dump(by_alias=True, mode="json"))

    if overwrite or not _valid_workflow_exists(spaces):
        spaces.save_json(WORKFLOW_ARTIFACT.key, WORKFLOW_ARTIFACT.model_dump(by_alias=True, mode="json"))

    eval_key = "evals/cases/research-quality-v1.json"
    if overwrite or not _valid_eval_cases_exist(spaces, eval_key):
        spaces.save_json(
            eval_key,
            {"version": WORKFLOW_VERSION, "cases": [case.model_dump(by_alias=True) for case in EVALUATION_CASES]},
        )

    return load_memory_overview(spaces, update_applications=[], warnings=warnings)


def load_memory_context(
    spaces: SpacesClient,
    *,
    approved_update_count: int = 0,
) -> MemoryContext:
    overview = load_memory_overview(spaces, update_applications=[])
    return MemoryContext(
        workflowVersion=overview.workflow.version if overview.workflow else WORKFLOW_VERSION,
        instructionVersion=_version_for(overview.documents, "instructions"),
        sourcePolicyVersion=_version_for(overview.documents, "source_policy"),
        notionFormattingVersion=_version_for(overview.documents, "notion_formatting"),
        learningOutputVersion=_version_for(overview.documents, "learning_output"),
        documents=overview.documents,
        toolConfigs=overview.tool_configs,
        workflow=overview.workflow,
        approvedUpdateCount=approved_update_count,
        warnings=overview.warnings,
    )


def load_memory_overview(
    spaces: SpacesClient,
    *,
    update_applications: list[UpdateApplicationRecord],
    warnings: list[str] | None = None,
) -> MemoryOverview:
    warnings = warnings or []
    documents = [_load_text_document(spaces, document, warnings) for document in TEXT_DOCUMENTS]
    tool_configs = [_load_tool_config(spaces, config, warnings) for config in TOOL_CONFIGS]
    workflow = _load_workflow(spaces, warnings)
    return MemoryOverview(
        documents=documents,
        toolConfigs=tool_configs,
        workflow=workflow,
        updateApplications=update_applications,
        warnings=warnings,
    )


def list_evaluation_cases(spaces: SpacesClient) -> list[EvaluationCase]:
    payload = spaces.get_json("evals/cases/research-quality-v1.json") if spaces.enabled else None
    if isinstance(payload, dict) and isinstance(payload.get("cases"), list):
        return [EvaluationCase.model_validate(case) for case in payload["cases"]]
    return EVALUATION_CASES


def run_quality_evaluations(
    *,
    run_id: str | None,
    report_markdown: str | None,
    cases: list[EvaluationCase],
) -> list[EvaluationResult]:
    report = (report_markdown or "").lower()
    results: list[EvaluationResult] = []
    for case in cases:
        if not case.active:
            continue
        expected_hits = [signal for signal in case.expected_signals if signal.lower() in report]
        forbidden_hits = [signal for signal in case.forbidden_signals if signal.lower() in report]
        total_checks = max(1, len(case.expected_signals) + len(case.forbidden_signals))
        score = (len(expected_hits) + (len(case.forbidden_signals) - len(forbidden_hits))) / total_checks
        if not report_markdown:
            status = "warning"
            summary = "No completed report was available for evaluation."
        elif forbidden_hits:
            status = "fail"
            summary = f"Forbidden signal(s) found: {', '.join(forbidden_hits)}."
        elif score >= 0.75:
            status = "pass"
            summary = f"Quality signals matched: {', '.join(expected_hits) or 'baseline checks'}."
        else:
            status = "fail"
            missing = [signal for signal in case.expected_signals if signal not in expected_hits]
            summary = f"Missing expected signal(s): {', '.join(missing)}."
        results.append(
            EvaluationResult(
                id=f"eval_result_{uuid.uuid4().hex[:12]}",
                caseId=case.id,
                status=status,
                score=round(score, 3),
                summary=summary,
                runId=run_id,
                evidence=expected_hits + [f"forbidden:{hit}" for hit in forbidden_hits],
            )
        )
    return results


def save_evaluation_results(
    spaces: SpacesClient,
    *,
    run_id: str | None,
    results: list[EvaluationResult],
) -> list[EvaluationResult]:
    if not spaces.enabled:
        return results
    for result in results:
        key = dated_artifact_key("evals/results", run_id or "manual", result.id, "json")
        if spaces.save_json(key, result.model_dump(by_alias=True, mode="json")):
            result.artifact_key = key
    return results


def sync_approved_update_to_spaces(
    spaces: SpacesClient,
    update: ProposedUpdate,
    *,
    workflow_version: str | None,
) -> dict[str, str | None]:
    runtime_categories = {"instructions", "source_policy", "workflow", "notion_formatting", "user_preference", "evaluation"}
    if update.category in runtime_categories:
        key = _runtime_update_key(update)
        body = _approved_update_markdown(update)
        saved_key = spaces.save_markdown(key, body) if spaces.enabled else None
        workflow_key = None
        if update.category in {"workflow", "instructions", "source_policy", "user_preference", "evaluation"}:
            workflow_key = f"workflows/versions/{workflow_version or f'research-workflow-{update.id}'}.json"
            payload = {
                "version": workflow_version or f"research-workflow-{update.id}",
                "status": "active",
                "approvedUpdateId": update.id,
                "category": update.category,
                "title": update.title,
                "summary": update.body[:900],
                "createdAt": datetime.now(timezone.utc).isoformat(),
            }
            if spaces.enabled:
                spaces.save_json(workflow_key, payload)
        return {
            "status": "runtime_applied",
            "memory_key": saved_key or key,
            "artifact_key": workflow_key or saved_key or key,
            "summary": f"Approved {update.category} update synced to runtime memory.",
        }

    key = f"backlog/approved/{update.id}.md"
    saved_key = spaces.save_markdown(key, _approved_update_markdown(update)) if spaces.enabled else None
    return {
        "status": "backlog_recorded",
        "memory_key": saved_key or key,
        "artifact_key": saved_key or key,
        "summary": f"Approved {update.category} update recorded as deployment backlog.",
    }


def memory_context_as_prompt(memory_context: MemoryContext | None) -> str:
    if not memory_context:
        return "- Bundled code instructions are active; memory context was unavailable."
    lines = [
        f"Workflow version: {memory_context.workflow_version}",
        f"Instruction version: {memory_context.instruction_version}",
        f"Source policy version: {memory_context.source_policy_version}",
        f"Notion formatting version: {memory_context.notion_formatting_version}",
        f"Learning output version: {memory_context.learning_output_version}",
        f"Approved runtime updates loaded: {memory_context.approved_update_count}",
    ]
    for document in memory_context.documents:
        lines.append(f"\n## {document.title} ({document.key})\n{document.content or document.summary}")
    if memory_context.workflow:
        lines.append(f"\n## Active workflow\n{memory_context.workflow.summary}\nPhases: {', '.join(memory_context.workflow.phases)}")
    return "\n".join(lines)


def _load_text_document(spaces: SpacesClient, default: MemoryDocument, warnings: list[str]) -> MemoryDocument:
    if spaces.enabled:
        content = spaces.get_text(default.key)
        if content is not None:
            return default.model_copy(update={"content": content, "status": "active", "updated_at": datetime.now(timezone.utc)})
        warnings.append(f"Missing Spaces memory document {default.key}; using bundled default.")
    return default.model_copy(update={"status": "default"})


def _load_tool_config(spaces: SpacesClient, default: ToolConfigRecord, warnings: list[str]) -> ToolConfigRecord:
    if spaces.enabled:
        payload = spaces.get_json(default.key)
        if isinstance(payload, dict):
            try:
                return ToolConfigRecord.model_validate(payload)
            except Exception:  # noqa: BLE001
                warnings.append(f"Invalid Spaces tool config {default.key}; using bundled default.")
        warnings.append(f"Missing Spaces tool config {default.key}; using bundled default.")
    return default


def _load_workflow(spaces: SpacesClient, warnings: list[str]) -> WorkflowVersionArtifact:
    if spaces.enabled:
        payload = spaces.get_json(WORKFLOW_ARTIFACT.key)
        if isinstance(payload, dict):
            try:
                return WorkflowVersionArtifact.model_validate(payload)
            except Exception:  # noqa: BLE001
                warnings.append(f"Invalid Spaces workflow {WORKFLOW_ARTIFACT.key}; using bundled default.")
        warnings.append(f"Missing Spaces workflow {WORKFLOW_ARTIFACT.key}; using bundled default.")
    return WORKFLOW_ARTIFACT


def _valid_workflow_exists(spaces: SpacesClient) -> bool:
    if not spaces.object_exists(WORKFLOW_ARTIFACT.key):
        return False
    payload = spaces.get_json(WORKFLOW_ARTIFACT.key)
    if not isinstance(payload, dict):
        return False
    try:
        WorkflowVersionArtifact.model_validate(payload)
        return True
    except Exception:  # noqa: BLE001
        return False


def _valid_eval_cases_exist(spaces: SpacesClient, key: str) -> bool:
    if not spaces.object_exists(key):
        return False
    payload = spaces.get_json(key)
    if not isinstance(payload, dict) or not isinstance(payload.get("cases"), list):
        return False
    try:
        [EvaluationCase.model_validate(case) for case in payload["cases"]]
        return True
    except Exception:  # noqa: BLE001
        return False


def _version_for(documents: list[MemoryDocument], category: str) -> str:
    document = next((item for item in documents if item.category == category), None)
    return document.version if document else WORKFLOW_VERSION


def _runtime_update_key(update: ProposedUpdate) -> str:
    folders = {
        "instructions": "instructions/approved",
        "source_policy": "instructions/source-policy-updates",
        "workflow": "workflows/approved",
        "notion_formatting": "instructions/notion-formatting-updates",
        "user_preference": "instructions/user-preference-updates",
        "evaluation": "evals/approved",
    }
    return f"{folders.get(update.category, 'instructions/approved')}/{update.id}.md"


def _approved_update_markdown(update: ProposedUpdate) -> str:
    return f"""# {update.title}

- Update ID: {update.id}
- Category: {update.category}
- Status: {update.status}
- Evidence runs: {', '.join(update.evidence_run_ids) or 'none'}

{update.body}
"""
