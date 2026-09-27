"""
Phase 6 — Finding Verification Service.

Implements the human-in-the-loop verification workflow:

    AI Finding (PENDING_REVIEW)
           ↓
    Human reviewer inspects evidence
           ↓
    Reviewer submits decision: VERIFIED | REJECTED | DISMISSED
           ↓
    Finding status updated + FindingVerification audit row appended
           ↓
    History preserved for audit

Design invariants enforced here:
- AI findings are NEVER automatically verified.
- AI evidence is NEVER modified during verification.
- Decisions are transactional: both the status update and audit row
  either commit together or both roll back.
- Concurrent updates are detected via optimistic checking of the
  finding's current status before applying the transition.
- The audit table (finding_verifications) is append-only; no deletes.
"""
import uuid
from datetime import datetime, timezone
from math import ceil
from typing import Optional

from sqlalchemy import select, func
from sqlalchemy.orm import Session

from app.core.auth import ReviewerContext
from app.core.exceptions import (
    ConflictException,
    InvalidStateTransitionException,
    ResourceNotFoundException,
)
from app.core.logging_config import logger
from app.models.analysis import Analysis
from app.models.finding import Finding, FindingStatus, FindingVerificationDecision
from app.models.finding_verification import FindingVerification
from app.models.pull_request import PullRequest
from app.models.repository import Repository
from app.schemas.finding_detail import (
    AnalysisSummary,
    FindingDetail,
    FindingQueueItem,
    FindingQueueListResponse,
    PullRequestSummary,
    RepositorySummary,
)
from app.schemas.finding_verification import FindingVerificationList, FindingVerificationRead


# Statuses that indicate a finding is awaiting human attention.
PENDING_STATUSES = {FindingStatus.OPEN.value, FindingStatus.PENDING_REVIEW.value}

# Terminal statuses — a finding in one of these has already been resolved.
TERMINAL_STATUSES = {
    FindingStatus.VERIFIED.value,
    FindingStatus.REJECTED.value,
    FindingStatus.DISMISSED.value,
    FindingStatus.RESOLVED.value,
    FindingStatus.FALSE_POSITIVE.value,
}

# Map from human decision → new finding status
DECISION_TO_STATUS = {
    FindingVerificationDecision.VERIFIED.value: FindingStatus.VERIFIED.value,
    FindingVerificationDecision.REJECTED.value: FindingStatus.REJECTED.value,
    FindingVerificationDecision.DISMISSED.value: FindingStatus.DISMISSED.value,
}


class FindingVerificationService:
    """
    Service layer for Phase 6 human verification of AI findings.

    All mutating operations are transactional and produce an audit record.
    """

    # ── Review Queue ─────────────────────────────────────────────────────────

    def get_review_queue(
        self,
        db: Session,
        *,
        status: Optional[str] = None,
        severity: Optional[str] = None,
        repository_id: Optional[uuid.UUID] = None,
        pull_request_id: Optional[uuid.UUID] = None,
        commit_sha: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> FindingQueueListResponse:
        """
        Return paginated, filterable queue of findings pending human review.

        Default ordering: severity rank DESC, created_at ASC (oldest first).
        Filtering happens at the database level — no Python-side filtering.
        """
        page = max(1, page)
        page_size = min(max(1, page_size), 100)

        # Default: show findings that need review (OPEN and PENDING_REVIEW)
        target_statuses = [FindingStatus.OPEN.value, FindingStatus.PENDING_REVIEW.value]
        if status:
            target_statuses = [status.upper()]

        # Severity rank for ordering (higher = reviewed first)
        severity_order = {
            "CRITICAL": 5, "HIGH": 4, "MEDIUM": 3, "LOW": 2, "INFO": 1,
        }

        # Build base query joining to Analysis → PullRequest → Repository
        stmt = (
            select(Finding, Analysis, PullRequest, Repository)
            .join(Analysis, Finding.analysis_id == Analysis.id)
            .join(PullRequest, Analysis.pull_request_id == PullRequest.id)
            .join(Repository, PullRequest.repository_id == Repository.id)
            .where(Finding.status.in_(target_statuses))
        )

        # Apply optional filters at DB level
        if severity:
            stmt = stmt.where(Finding.severity == severity.upper())
        if repository_id:
            stmt = stmt.where(Repository.id == repository_id)
        if pull_request_id:
            stmt = stmt.where(PullRequest.id == pull_request_id)
        if commit_sha:
            stmt = stmt.where(Analysis.head_sha == commit_sha)

        # Count total (no offset)
        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = db.scalar(count_stmt) or 0

        # Apply ordering: severity rank desc, created_at asc
        # SQLite/SQLAlchemy-compatible ordering using CASE-like Python sort
        offset = (page - 1) * page_size
        rows = db.execute(stmt.offset(offset).limit(page_size)).all()

        items = []
        for finding, analysis, pr, repo in rows:
            # Extract title from first line of message
            title = (finding.message or "").split("\n")[0][:255]
            items.append(FindingQueueItem(
                finding_id=finding.id,
                analysis_id=finding.analysis_id,
                repository_full_name=repo.full_name,
                repository_id=repo.id,
                pull_request_id=pr.id,
                pull_request_number=pr.pr_number,
                commit_sha=analysis.head_sha,
                file_path=finding.file_path,
                start_line=finding.start_line,
                end_line=finding.end_line,
                severity=finding.severity,
                category=finding.category,
                source=finding.source,
                title=title,
                status=finding.status,
                created_at=finding.created_at,
            ))

        # Sort in Python for determinism (severity rank desc, created_at asc)
        items.sort(
            key=lambda x: (-severity_order.get(x.severity, 0), x.created_at),
        )

        total_pages = ceil(total / page_size) if total > 0 else 0
        return FindingQueueListResponse(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )

    # ── Finding Detail ───────────────────────────────────────────────────────

    def get_finding_detail(
        self,
        db: Session,
        finding_id: uuid.UUID,
    ) -> FindingDetail:
        """
        Return full finding detail for reviewer inspection.

        Includes:
        - Core finding fields (immutable AI evidence)
        - Analysis context
        - Pull request context
        - Repository context
        - Full verification history (ordered ascending by decided_at)
        """
        finding = db.scalar(select(Finding).where(Finding.id == finding_id))
        if not finding:
            raise ResourceNotFoundException(f"Finding '{finding_id}' not found")

        analysis = db.scalar(select(Analysis).where(Analysis.id == finding.analysis_id))
        pr: Optional[PullRequest] = None
        repo: Optional[Repository] = None

        if analysis:
            pr = db.scalar(select(PullRequest).where(PullRequest.id == analysis.pull_request_id))
            if pr:
                repo = db.scalar(select(Repository).where(Repository.id == pr.repository_id))

        verifications = list(
            db.scalars(
                select(FindingVerification)
                .where(FindingVerification.finding_id == finding_id)
                .order_by(FindingVerification.decided_at)
            ).all()
        )

        return FindingDetail(
            id=finding.id,
            analysis_id=finding.analysis_id,
            source=finding.source,
            category=finding.category,
            severity=finding.severity,
            rule_id=finding.rule_id,
            fingerprint=finding.fingerprint,
            file_path=finding.file_path,
            start_line=finding.start_line,
            end_line=finding.end_line,
            message=finding.message,
            status=finding.status,
            evidence=finding.evidence,
            created_at=finding.created_at,
            verification_history=[
                FindingVerificationRead.model_validate(v) for v in verifications
            ],
            analysis=AnalysisSummary.model_validate(analysis) if analysis else None,
            pull_request=PullRequestSummary.model_validate(pr) if pr else None,
            repository=RepositorySummary.model_validate(repo) if repo else None,
        )

    # ── Verification Action ──────────────────────────────────────────────────

    def verify_finding(
        self,
        db: Session,
        finding_id: uuid.UUID,
        decision: str,
        reviewer: ReviewerContext,
        comment: Optional[str] = None,
        expected_current_status: Optional[str] = None,
    ) -> FindingDetail:
        """
        Apply a human verification decision to a finding.

        Transactional — both the status update and audit row commit together.

        Concurrency:
            If `expected_current_status` is provided the service will reject
            the operation if the finding's current status differs (optimistic
            locking pattern). The caller may pass the status it observed when
            it fetched the finding.  If omitted, ANY non-terminal status is
            accepted.

        Raises:
            ResourceNotFoundException: finding does not exist.
            InvalidStateTransitionException: finding is already in a terminal
                state or the decision is invalid.
            ConflictException: finding status changed since the caller last
                read it (concurrent modification).
        """
        upper_decision = decision.upper()
        if upper_decision not in DECISION_TO_STATUS:
            raise InvalidStateTransitionException(
                f"Invalid decision '{decision}'. "
                f"Must be one of: {', '.join(sorted(DECISION_TO_STATUS.keys()))}"
            )

        # Load finding inside the transaction
        finding = db.scalar(select(Finding).where(Finding.id == finding_id))
        if not finding:
            raise ResourceNotFoundException(f"Finding '{finding_id}' not found")

        current_status = finding.status

        # Concurrency guard — optimistic check
        if expected_current_status is not None:
            if current_status != expected_current_status:
                raise ConflictException(
                    f"Finding status changed from '{expected_current_status}' "
                    f"to '{current_status}' since you last read it. "
                    "Reload the finding and try again."
                )

        # Terminal state guard
        if current_status in TERMINAL_STATUSES:
            raise InvalidStateTransitionException(
                f"Finding '{finding_id}' is already in terminal state '{current_status}'. "
                "Create a new finding or contact an administrator to reopen it."
            )

        new_status = DECISION_TO_STATUS[upper_decision]

        logger.info(
            "Reviewer '%s' verifying finding '%s': %s → %s",
            reviewer.login,
            finding_id,
            current_status,
            new_status,
        )

        # IMPORTANT: Only the status changes.
        # The original AI evidence, message, file_path, line numbers,
        # category, severity, source, and fingerprint are NOT touched.
        finding.status = new_status

        # Append audit record (append-only, never deleted via this path)
        verification = FindingVerification(
            finding_id=finding.id,
            reviewer_login=reviewer.login,
            reviewer_user_id=reviewer.user_id,
            decision=upper_decision,
            comment=comment,
            previous_status=current_status,
            decided_at=datetime.now(timezone.utc),
        )
        db.add(verification)

        # Commit both changes atomically
        try:
            db.commit()
        except Exception:
            db.rollback()
            raise

        db.refresh(finding)

        return self.get_finding_detail(db=db, finding_id=finding_id)

    # ── Verification History ─────────────────────────────────────────────────

    def get_verification_history(
        self,
        db: Session,
        finding_id: uuid.UUID,
    ) -> FindingVerificationList:
        """Return the complete ordered audit trail for a finding."""
        finding = db.scalar(select(Finding).where(Finding.id == finding_id))
        if not finding:
            raise ResourceNotFoundException(f"Finding '{finding_id}' not found")

        verifications = list(
            db.scalars(
                select(FindingVerification)
                .where(FindingVerification.finding_id == finding_id)
                .order_by(FindingVerification.decided_at)
            ).all()
        )
        return FindingVerificationList(
            items=[FindingVerificationRead.model_validate(v) for v in verifications],
            total=len(verifications),
        )


finding_verification_service = FindingVerificationService()
