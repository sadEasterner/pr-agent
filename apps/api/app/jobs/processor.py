from __future__ import annotations

import time

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.ai.client import create_ai_provider
from app.ai.diff import prepare_diff_bundle
from app.ai.reviewer import AiReviewer
from app.config import Settings
from app.db.models import PullRequest, WebhookEvent
from app.gitea.client import GiteaClient
from app.gitea.service import GiteaService
from app.logging import get_logger
from app.policy.engine import AutomationAction, PolicyEngine
from app.reviews.comments import render_review
from app.reviews.store import ReviewStore
from app.rules.engine import RulesEngine
from app.rules.loader import LoadedRules
from app.runtime import get_runtime_controls
from app.scm.base import ScmProvider
from app.webhooks.schemas import PullRequestEvent

logger = get_logger(__name__)


class ReviewProcessor:
    def __init__(
        self,
        settings: Settings,
        session_factory: async_sessionmaker[AsyncSession],
        loaded_rules: LoadedRules,
        scm: ScmProvider | GiteaClient,
        ai_reviewer: AiReviewer | None = None,
    ) -> None:
        self.settings = settings
        self.session_factory = session_factory
        self.loaded_rules = loaded_rules
        self.scm = GiteaService(scm) if isinstance(scm, GiteaClient) else scm
        self.rules = RulesEngine(loaded_rules)
        self.policy = PolicyEngine(loaded_rules.global_rules.automation)
        self.ai_reviewer = ai_reviewer or AiReviewer(
            settings,
            loaded_rules,
            create_ai_provider(settings) if settings.ai_enabled else None,
        )

    async def process(self, event: PullRequestEvent, force: bool = False) -> None:
        repository = event.repository_name
        number = event.pr_number
        if not repository or number is None:
            logger.warning("job_missing_identity")
            return
        started = time.perf_counter()
        logger.info(
            "job_start",
            repository=repository,
            pr_number=number,
            event_type=event.event_type,
            head_sha=event.head_sha,
        )
        async with self.session_factory() as session:
            if not force and not await self._claim_event(session, event):
                logger.info(
                    "duplicate_webhook",
                    repository=repository,
                    pr_number=number,
                    event_type=event.event_type,
                    head_sha=event.head_sha,
                )
                return
            try:
                snapshot = await self.scm.fetch_snapshot(repository, number)
            except Exception:
                logger.exception(
                    "scm_fetch_failed",
                    repository=repository,
                    pr_number=number,
                )
                return
            if snapshot.merged or snapshot.state.lower() in {"closed", "merged"}:
                logger.info(
                    "job_skipped_closed_pr",
                    repository=repository,
                    pr_number=number,
                    state=snapshot.state,
                    merged=snapshot.merged,
                )
                return
            store = ReviewStore(session)
            existing_pr = await session.execute(
                select(PullRequest).where(
                    PullRequest.repository == snapshot.repository,
                    PullRequest.number == snapshot.number,
                )
            )
            pull_request = existing_pr.scalar_one_or_none()
            if (
                pull_request
                and not force
                and await store.get_review_for_sha(pull_request.id, snapshot.head_sha)
            ):
                logger.info(
                    "duplicate_sha_review_skipped",
                    repository=repository,
                    pr_number=number,
                    head_sha=snapshot.head_sha,
                )
                await session.commit()
                return

            rules_result = self.rules.evaluate(snapshot)
            logger.info(
                "rules_executed",
                repository=repository,
                pr_number=number,
                head_sha=snapshot.head_sha,
                labels=rules_result.labels,
                violations=len(rules_result.violations),
            )
            controls = await get_runtime_controls(session, self.settings)
            bundle = prepare_diff_bundle(snapshot.files, snapshot.diff, self.settings)
            ai_result = await self.ai_reviewer.review(
                snapshot,
                rules_result,
                bundle,
                ai_enabled=controls.ai_enabled,
            )
            human_status = self.policy.assert_not_merge_authority(ai_result.recommendation.value)
            duration_ms = int((time.perf_counter() - started) * 1000)
            pull_request = await store.upsert_pull_request(
                snapshot,
                human_status,
                ai_result.risk.value,
                ai_result.recommendation.value,
            )
            review = await store.create_review(
                pull_request,
                snapshot,
                rules_result,
                ai_result,
                duration_ms,
                self.settings.ai_model if controls.ai_enabled else None,
                controls.ai_enabled,
                forced=force,
            )
            await session.commit()
            if self.policy.can(AutomationAction.ADD_LABELS) and rules_result.labels:
                try:
                    await self.scm.add_labels(repository, number, rules_result.labels)
                except Exception:
                    logger.exception("scm_labels_failed", repository=repository, pr_number=number)
            if controls.pr_comments_enabled and self.policy.can(AutomationAction.POST_REVIEW):
                body = render_review(snapshot, rules_result, ai_result, self.policy)
                try:
                    await self.scm.post_or_update_review_comment(repository, number, body)
                    logger.info(
                        "scm_comment_published",
                        repository=repository,
                        pr_number=number,
                        head_sha=snapshot.head_sha,
                    )
                except Exception:
                    logger.exception("scm_comment_failed", repository=repository, pr_number=number)
            elif not controls.pr_comments_enabled:
                logger.info(
                    "gitea_comment_skipped",
                    repository=repository,
                    pr_number=number,
                    head_sha=snapshot.head_sha,
                )
            logger.info(
                "job_complete",
                repository=repository,
                pr_number=number,
                head_sha=snapshot.head_sha,
                review_id=review.id,
                findings=len(ai_result.findings),
                processing_time_ms=duration_ms,
            )

    async def _claim_event(self, session: AsyncSession, event: PullRequestEvent) -> bool:
        sha = event.head_sha or "unknown"
        values = {
            "repository": event.repository_name,
            "pr_number": event.pr_number,
            "event_type": event.event_type,
            "head_sha": sha,
            "action": event.action,
            "status": "accepted",
        }
        dialect = session.bind.dialect.name if session.bind is not None else "sqlite"
        try:
            if dialect == "postgresql":
                stmt = (
                    pg_insert(WebhookEvent)
                    .values(**values)
                    .on_conflict_do_nothing(
                        constraint="uq_webhook_events_idempotency",
                    )
                    .returning(WebhookEvent.id)
                )
                result = await session.execute(stmt)
                claimed = result.scalar_one_or_none() is not None
                await session.commit()
                return claimed
            session.add(WebhookEvent(**values))
            await session.commit()
            return True
        except IntegrityError:
            await session.rollback()
            return False
