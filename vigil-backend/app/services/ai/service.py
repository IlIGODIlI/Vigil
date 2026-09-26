import uuid
import asyncio
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.models.analysis import Analysis, AnalysisStatus, AnalysisTrigger
from app.models.commit import Commit
from app.models.finding import Finding, FindingStatus, FindingSource
from app.integrations.repolens.service import repository_context_service
from app.services.ai.prompt import AnalysisPromptBuilder
from app.services.ai.provider import get_llm_provider
from app.integrations.github.client import github_client

class AIAnalysisService:
    def __init__(self):
        self.provider = get_llm_provider()

    async def run_analysis(self, db: Session, analysis_id: uuid.UUID, installation_id: int):
        analysis = db.scalar(select(Analysis).where(Analysis.id == analysis_id))
        if not analysis:
            return

        pr = analysis.pull_request
        owner = pr.repository.owner_login
        repo = pr.repository.name

        analysis.status = AnalysisStatus.RUNNING
        analysis.started_at = datetime.now(timezone.utc)
        db.commit()

        try:
            context = repository_context_service.get_context(pr.repository.full_name)
            if not context or context.commit_sha != analysis.head_sha:
                context = await repository_context_service.update_context_for_commit(
                    installation_id=installation_id,
                    owner=owner,
                    repo=repo,
                    sha=analysis.head_sha
                )

            commit_data = await github_client.get_commit(
                installation_id=installation_id,
                owner=owner,
                repo=repo,
                sha=analysis.head_sha
            )
            
            diff_files = []
            for f in commit_data.get("files", []):
                diff_files.append({
                    "filename": f.get("filename"),
                    "status": f.get("status"),
                    "additions": f.get("additions"),
                    "deletions": f.get("deletions"),
                    "patch": f.get("patch", "patch unavailable")
                })
            
            commit_info = {
                "sha": analysis.head_sha,
                "message": commit_data.get("commit", {}).get("message"),
                "files": diff_files
            }

            prompt = AnalysisPromptBuilder.build(context, commit_info)
            result = await self.provider.analyze_commit(prompt)

            for f in result.findings:
                finding = Finding(
                    analysis_id=analysis.id,
                    source=FindingSource.AI_REVIEW,
                    category=f.category,
                    severity=f.severity,
                    fingerprint=str(uuid.uuid4()), 
                    file_path=f.file_path,
                    start_line=f.start_line,
                    end_line=f.end_line,
                    message=f.title + "\n\n" + f.description,
                    # Phase 6: AI findings enter PENDING_REVIEW — never auto-verified
                    status=FindingStatus.PENDING_REVIEW,
                    evidence={"reasoning": f.reasoning, "evidence": f.evidence, "introduced_by_commit": f.introduced_by_commit}
                )
                db.add(finding)

            analysis.status = AnalysisStatus.COMPLETED
            analysis.completed_at = datetime.now(timezone.utc)
            db.commit()

        except Exception as e:
            analysis.status = AnalysisStatus.FAILED
            analysis.error_message = str(e)
            analysis.completed_at = datetime.now(timezone.utc)
            db.commit()

ai_analysis_service = AIAnalysisService()
