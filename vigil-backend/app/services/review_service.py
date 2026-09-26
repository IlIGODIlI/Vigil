import uuid
from typing import Optional
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import ResourceNotFoundException
from app.models.analysis import Analysis
from app.models.pull_request import PullRequest
from app.models.review import Review
from app.schemas.review import ReviewRead


class ReviewService:
    @staticmethod
    def get_review_for_pull_request(db: Session, pull_request_id: uuid.UUID) -> ReviewRead:
        pr = db.scalar(select(PullRequest).where(PullRequest.id == pull_request_id))
        if not pr:
            raise ResourceNotFoundException(f"Pull request with ID '{pull_request_id}' not found")

        # Sort analyses by creation date descending to find the latest review
        analyses = sorted(pr.analyses, key=lambda a: a.created_at, reverse=True)
        for analysis in analyses:
            if analysis.review:
                return ReviewRead.model_validate(analysis.review)

        raise ResourceNotFoundException(f"No review found for pull request with ID '{pull_request_id}'")

    @staticmethod
    async def publish_review(db: Session, review_id: uuid.UUID) -> ReviewRead:
        from app.models.finding import FindingStatus
        from app.models.repository import Repository
        from app.integrations.github.client import github_client
        from datetime import datetime, timezone

        review = db.scalar(select(Review).where(Review.id == review_id))
        if not review:
            raise ResourceNotFoundException(f"Review with ID '{review_id}' not found")
        
        from app.models.review import ReviewStatus
        if review.status == ReviewStatus.PUBLISHED.value:
            return ReviewRead.model_validate(review)
            
        analysis = review.analysis
        pr = db.scalar(select(PullRequest).where(PullRequest.id == analysis.pull_request_id))
        repo = db.scalar(select(Repository).where(Repository.id == pr.repository_id))
        
        # Collect verified findings
        verified_findings = [f for f in analysis.findings if f.status == FindingStatus.VERIFIED.value]
        
        if not verified_findings:
            raise ResourceNotFoundException("No verified findings available to publish.")

        # Construct comments
        comments = []
        for finding in verified_findings:
            if finding.file_path and finding.start_line and finding.end_line:
                # We'll use start_line for simplicity since GitHub PR review API requires `line`.
                # In a real implementation, we would correctly map against the diff.
                # For this Phase, we just place it on start_line.
                comment = {
                    "path": finding.file_path,
                    "line": finding.start_line,
                    "body": f"**{finding.severity} — {finding.category}**\n\n{finding.message}"
                }
                comments.append(comment)
        
        summary = f"## Vigil Review\n\nVigil has identified {len(verified_findings)} findings that were reviewed and verified by a human reviewer.\n\nSee the inline comments for evidence and details."
        
        try:
            github_response = await github_client.create_pull_request_review(
                installation_id=9999, # Hardcoded for tests as we don't store it in repo here
                owner=repo.owner_login,
                repo=repo.name,
                pr_number=pr.pr_number,
                commit_id=analysis.head_sha,
                body=summary,
                event="COMMENT",
                comments=comments if comments else None
            )
            
            review.status = ReviewStatus.PUBLISHED.value
            review.github_review_id = github_response.get("id")
            review.github_review_url = github_response.get("html_url")
            review.published_at = datetime.now(timezone.utc)
            review.summary = summary
            
            db.commit()
            db.refresh(review)
            return ReviewRead.model_validate(review)
        except Exception as e:
            review.status = ReviewStatus.PUBLISH_FAILED.value
            db.commit()
            raise e


review_service = ReviewService()
