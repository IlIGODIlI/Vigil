import asyncio
from datetime import datetime, timezone
import logging
from typing import Any, Dict, List, Optional
import uuid
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import ResourceNotFoundException
from app.integrations.github.client import GitHubClient, github_client
from app.integrations.repolens.service import RepositoryContextService, repository_context_service
from app.models.commit import Commit
from app.models.commit_analysis import CommitAnalysis, CommitAnalysisOverallStatus, CommitAnalysisStatus
from app.models.repository import Repository
from app.schemas.commit_analysis import CommitAnalysisRead

from app.services.commit_analysis.ai_boundary import CommitSemanticAnalyzerInterface, SafeAISemanticAnalyzerWrapper
from app.services.commit_analysis.completeness_engine import CompletenessSignalEngine
from app.services.commit_analysis.deterministic_analyzer import DeterministicAnalyzer
from app.services.commit_analysis.intent_classifier import classify_commit_intent
from app.services.commit_analysis.schemas import CommitAnalysisContext, CommitAnalysisResult

logger = logging.getLogger(__name__)


class CommitAnalysisEngineService:
    """
    Main orchestrator for commit analysis and completeness signals (Member 4).
    Integrates GitHub commit diffs, RepoLens repository context, deterministic analysis,
    AI semantic boundary, and CommitAnalysis DB model persistence.
    """

    def __init__(
        self,
        github_cl: Optional[GitHubClient] = None,
        repo_ctx_service: Optional[RepositoryContextService] = None,
        ai_analyzer: Optional[CommitSemanticAnalyzerInterface] = None,
    ):
        self.github_client = github_cl or github_client
        self.repo_context_service = repo_ctx_service or repository_context_service
        self.deterministic_analyzer = DeterministicAnalyzer()
        self.completeness_engine = CompletenessSignalEngine()
        self.ai_analyzer = SafeAISemanticAnalyzerWrapper(ai_analyzer)

    async def analyze_commit_async(
        self,
        db: Session,
        sha: str,
        installation_id: Optional[int] = None,
        owner: Optional[str] = None,
        repo: Optional[str] = None,
    ) -> CommitAnalysisRead:
        """
        Executes commit completeness analysis asynchronously and updates the DB record.
        """
        # 1. Lookup Commit in DB
        commits = list(db.scalars(select(Commit).where(Commit.sha == sha)).all())
        selected_commit: Optional[Commit] = None
        if commits:
            selected_commit = sorted(commits, key=lambda c: c.created_at, reverse=True)[0]

        # 2. Try syncing commit from GitHub if not found or if repository details provided
        if not selected_commit and installation_id and owner and repo:
            try:
                commit_data = await self.github_client.get_commit(
                    installation_id=installation_id, owner=owner, repo=repo, sha=sha
                )
                if commit_data:
                    from app.services.repository_service import repository_service
                    from app.services.commit_service import commit_service

                    repo_obj = repository_service.sync_repository_payload(
                        db=db,
                        repo_data={
                            "name": repo,
                            "owner": {"login": owner},
                            "id": commit_data.get("repository", {}).get("id", 0),
                        },
                    )
                    selected_commit = commit_service.sync_commit_payload(
                        db=db, repository=repo_obj, commit_data=commit_data
                    )
            except Exception as e:
                logger.warning("Could not fetch commit %s from GitHub API: %s", sha, str(e))

        if not selected_commit:
            raise ResourceNotFoundException(f"Commit with SHA '{sha}' not found")

        # 3. Create or update CommitAnalysis DB record in RUNNING state
        commit_analysis = db.scalar(
            select(CommitAnalysis)
            .where(CommitAnalysis.commit_id == selected_commit.id)
            .order_by(CommitAnalysis.created_at.desc())
        )
        now = datetime.now(timezone.utc)
        if not commit_analysis:
            commit_analysis = CommitAnalysis(
                id=uuid.uuid4(),
                commit_id=selected_commit.id,
                status=CommitAnalysisStatus.RUNNING.value,
                overall_status=CommitAnalysisOverallStatus.INSUFFICIENT_EVIDENCE.value,
                started_at=now,
                created_at=now,
            )
            db.add(commit_analysis)
        else:
            commit_analysis.status = CommitAnalysisStatus.RUNNING.value
            commit_analysis.started_at = now

        db.commit()
        db.refresh(commit_analysis)

        # 4. Gather Commit Context & Diffs
        changed_files: List[Dict[str, Any]] = []
        full_diff = ""
        repo_full_name = ""

        if selected_commit.repository:
            repo_full_name = selected_commit.repository.full_name
            inst_id = installation_id or 1  # Fallback to default if unassigned

            try:
                commit_data = await self.github_client.get_commit(
                    installation_id=inst_id,
                    owner=selected_commit.repository.owner_login,
                    repo=selected_commit.repository.name,
                    sha=sha,
                )
                if isinstance(commit_data, dict):
                    raw_files = commit_data.get("files", [])
                    for f in raw_files:
                        if isinstance(f, dict):
                            changed_files.append({
                                "filename": f.get("filename"),
                                "status": f.get("status"),
                                "additions": f.get("additions"),
                                "deletions": f.get("deletions"),
                                "patch": f.get("patch", ""),
                            })
                            if f.get("patch"):
                                full_diff += f"\n--- {f.get('filename')}\n+++ {f.get('filename')}\n{f.get('patch')}"
            except Exception as e:
                logger.info("GitHub API fetch omitted or failed for commit %s: %s", sha, str(e))

        # 5. Fetch Repository Context (RepoLens)
        repo_ctx = None
        if repo_full_name:
            repo_ctx = self.repo_context_service.get_context(repo_full_name)

        # 6. Build CommitAnalysisContext
        context = CommitAnalysisContext(
            commit_sha=sha,
            commit_message=selected_commit.message or "",
            changed_files=changed_files,
            diff=full_diff,
            repository_context=repo_ctx,
        )

        try:
            # 7. Intent Classification
            intent = classify_commit_intent(
                message=context.commit_message,
                changed_files=context.changed_files,
                diff=context.diff,
            )

            # 8. Deterministic Analysis
            signals = self.deterministic_analyzer.analyze(context)

            # 9. AI Semantic Analysis (Safe boundary check)
            semantic_notes = await self.ai_analyzer.analyze_semantic_consistency(context) or ""

            # 10. Completeness Engine Aggregation
            analysis_result: CommitAnalysisResult = self.completeness_engine.process(
                context=context,
                intent=intent,
                signals=signals,
                semantic_notes=semantic_notes,
            )

            # 11. Persist Results to DB
            commit_analysis.status = CommitAnalysisStatus.COMPLETED.value
            commit_analysis.overall_status = analysis_result.overall_status.value
            commit_analysis.summary = analysis_result.summary
            commit_analysis.implementation_notes = analysis_result.implementation_notes
            commit_analysis.testing_notes = analysis_result.testing_notes
            commit_analysis.error_handling_notes = analysis_result.error_handling_notes
            commit_analysis.documentation_notes = analysis_result.documentation_notes
            commit_analysis.placeholder_notes = analysis_result.placeholder_notes
            commit_analysis.signals = {
                "intent": analysis_result.intent.value,
                "signals": [s.model_dump() for s in analysis_result.completeness_signals],
            }
            commit_analysis.completed_at = datetime.now(timezone.utc)
            db.commit()
            db.refresh(commit_analysis)

        except Exception as e:
            logger.error("Commit completeness analysis failed for SHA %s: %s", sha, str(e), exc_info=True)
            commit_analysis.status = CommitAnalysisStatus.FAILED.value
            commit_analysis.overall_status = CommitAnalysisOverallStatus.INSUFFICIENT_EVIDENCE.value
            commit_analysis.summary = f"Analysis failed: {str(e)}"
            commit_analysis.completed_at = datetime.now(timezone.utc)
            db.commit()
            db.refresh(commit_analysis)

        return CommitAnalysisRead.model_validate(commit_analysis)

    def trigger_commit_analysis_sync(
        self,
        db: Session,
        sha: str,
        installation_id: Optional[int] = None,
        owner: Optional[str] = None,
        repo: Optional[str] = None,
    ) -> CommitAnalysisRead:
        """
        Synchronous wrapper around analyze_commit_async for backward compatibility with REST API endpoints.
        """
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        if loop.is_running():
            # If called inside an existing running event loop
            import nest_asyncio
            nest_asyncio.apply()
            return loop.run_until_complete(
                self.analyze_commit_async(db, sha, installation_id, owner, repo)
            )
        else:
            return loop.run_until_complete(
                self.analyze_commit_async(db, sha, installation_id, owner, repo)
            )


commit_analysis_engine_service = CommitAnalysisEngineService()
