import uuid
from typing import List, Optional
from sqlalchemy import select, func
from sqlalchemy.orm import Session

from app.core.exceptions import ResourceNotFoundException
from app.models.commit import Commit
from app.models.commit_analysis import CommitAnalysis, CommitAnalysisOverallStatus, CommitAnalysisStatus
from app.models.pull_request import PullRequest
from app.schemas.commit import CommitListResponse, CommitRead
from app.schemas.commit_analysis import CommitAnalysisRead


class CommitService:
    @staticmethod
    def get_commits_for_pull_request(
        db: Session, pull_request_id: uuid.UUID, page: int = 1, page_size: int = 20
    ) -> CommitListResponse:
        pr = db.scalar(select(PullRequest).where(PullRequest.id == pull_request_id))
        if not pr:
            raise ResourceNotFoundException(f"Pull request with ID '{pull_request_id}' not found")

        page = max(1, page)
        page_size = min(max(1, page_size), 100)
        offset = (page - 1) * page_size

        total = len(pr.commits)
        commits = pr.commits[offset : offset + page_size]
        total_pages = (total + page_size - 1) // page_size if total > 0 else 0

        return CommitListResponse(
            items=[CommitRead.model_validate(c) for c in commits],
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )

    @staticmethod
    def get_commit_by_sha(db: Session, sha: str) -> CommitRead:
        commits = list(db.scalars(select(Commit).where(Commit.sha == sha)).all())
        if not commits:
            raise ResourceNotFoundException(f"Commit with SHA '{sha}' not found")
        # Return the most recent commit by created_at if multiple exist across repositories
        selected_commit = sorted(commits, key=lambda c: c.created_at, reverse=True)[0]
        return CommitRead.model_validate(selected_commit)

    @staticmethod
    def trigger_commit_analysis(db: Session, sha: str) -> CommitAnalysisRead:
        commits = list(db.scalars(select(Commit).where(Commit.sha == sha)).all())
        if not commits:
            raise ResourceNotFoundException(f"Commit with SHA '{sha}' not found")
        selected_commit = sorted(commits, key=lambda c: c.created_at, reverse=True)[0]

        commit_analysis = CommitAnalysis(
            commit_id=selected_commit.id,
            status=CommitAnalysisStatus.QUEUED.value,
            overall_status=CommitAnalysisOverallStatus.INSUFFICIENT_EVIDENCE.value,
        )
        db.add(commit_analysis)
        db.commit()
        db.refresh(commit_analysis)

        return CommitAnalysisRead.model_validate(commit_analysis)


commit_service = CommitService()
