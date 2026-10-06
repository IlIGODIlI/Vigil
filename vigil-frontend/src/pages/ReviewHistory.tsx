import { useMemo, useState } from "react"
import {
  ArrowUpRight,
  CheckCircle,
  ChevronDown,
  Clock,
  Search,
  ShieldAlert,
  User,
  XCircle,
} from "lucide-react"
import { OrbXS } from "../components/AIOrb"
import PageHeader from "../components/PageHeader"

const reviews = [
  {
    id: "R-028",
    pr: 39,
    title: "chore: update CI pipeline config",
    repo: "infrastructure",
    reviewer: "Dev Kapoor",
    decision: "approved",
    findings: 0,
    date: "Sep 24, 2026",
    time: "14:32",
    duration: "12 min",
    aiStatus: "complete",
    humanNote:
      "No security findings required follow-up in the reviewed configuration changes.",
  },
  {
    id: "R-027",
    pr: 35,
    title: "feat: add OAuth2 provider support",
    repo: "auth-service",
    reviewer: "Priya Sharma",
    decision: "changes_requested",
    findings: 2,
    date: "Sep 23, 2026",
    time: "16:45",
    duration: "28 min",
    aiStatus: "complete",
    humanNote:
      "OAuth state validation requires changes before the pull request can proceed.",
  },
  {
    id: "R-026",
    pr: 31,
    title: "fix: resolve memory leak in cache",
    repo: "api-gateway",
    reviewer: "Rohan Mehta",
    decision: "approved",
    findings: 0,
    date: "Sep 22, 2026",
    time: "10:18",
    duration: "8 min",
    aiStatus: "complete",
    humanNote:
      "The reviewer found no security findings requiring changes in the analyzed diff.",
  },
  {
    id: "R-025",
    pr: 28,
    title: "feat: add export to CSV endpoint",
    repo: "data-pipeline",
    reviewer: "Anita Bose",
    decision: "escalated",
    findings: 1,
    date: "Sep 21, 2026",
    time: "11:54",
    duration: "19 min",
    aiStatus: "complete",
    humanNote:
      "A potential CSV injection finding was sent for additional human review.",
  },
  {
    id: "R-024",
    pr: 25,
    title: "deps: upgrade SQLAlchemy to 2.0",
    repo: "auth-service",
    reviewer: "Dev Kapoor",
    decision: "approved",
    findings: 0,
    date: "Sep 20, 2026",
    time: "09:10",
    duration: "15 min",
    aiStatus: "complete",
    humanNote:
      "The reviewer approved after checking the dependency change and analysis results.",
  },
]

type Decision = "approved" | "changes_requested" | "escalated"
type DecisionFilter = "all" | Decision

const decisionConfig: Record<Decision, {
  label: string
  icon: React.ElementType
  className: string
}> = {
  approved: { label: "Approved", icon: CheckCircle, className: "is-approved" },
  changes_requested: {
    label: "Changes Requested",
    icon: XCircle,
    className: "is-changes-requested",
  },
  escalated: {
    label: "Escalated",
    icon: ArrowUpRight,
    className: "is-escalated",
  },
}

function durationMinutes(duration: string) {
  return Number.parseInt(duration, 10) || 0
}

export default function ReviewHistory() {
  const [filter, setFilter] = useState<DecisionFilter>("all")
  const [query, setQuery] = useState("")
  const [repository, setRepository] = useState("all")

  const repositories = useMemo(
    () => Array.from(new Set(reviews.map((review) => review.repo))).sort(),
    [],
  )
  const totalFindings = reviews.reduce(
    (total, review) => total + review.findings,
    0,
  )
  const averageReviewTime = reviews.length
    ? reviews.reduce(
        (total, review) => total + durationMinutes(review.duration),
        0,
      ) / reviews.length
    : 0

  const visibleReviews = reviews.filter((review) => {
    const normalizedQuery = query.trim().toLowerCase()
    const matchesDecision = filter === "all" || review.decision === filter
    const matchesRepository = repository === "all" || review.repo === repository
    const matchesQuery =
      !normalizedQuery ||
      [review.id, review.title, review.repo, review.reviewer, `PR ${review.pr}`]
        .join(" ")
        .toLowerCase()
        .includes(normalizedQuery)
    return matchesDecision && matchesRepository && matchesQuery
  })

  const summary = [
    {
      value: reviews.length,
      label: "Total Reviews",
      note: "Pull-request security reviews",
    },
    {
      value: totalFindings,
      label: "Findings Reviewed",
      note: "Across completed reviews",
    },
    {
      value: `${averageReviewTime.toFixed(1)}m`,
      label: "Average Review Time",
      note: "From review start to decision",
    },
    {
      value: repositories.length,
      label: "Repositories Reviewed",
      note: "In this review history",
    },
  ]

  return (
    <div className="stage3-page">
      <PageHeader
        title="Review History"
        subtitle="Complete audit trail of security reviews"
      />

      <div className="stage3-stat-grid review-history-summary">
        {summary.map((item) => (
          <div key={item.label}>
            <strong>{item.value}</strong>
            <span>{item.label}</span>
            <small>{item.note}</small>
          </div>
        ))}
      </div>

      <div className="review-history-controls">
        <label className="review-history-search">
          <Search size={13} />
          <input
            className="input"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Search reviews, PRs, repositories, or reviewers"
            aria-label="Search review history"
          />
        </label>

        <div
          className="review-history-decisions"
          aria-label="Filter by human decision"
        >
          {(["all", "approved", "changes_requested", "escalated"] as const).map(
            (value) => (
              <button
                key={value}
                className={`btn btn-sm ${
                  filter === value ? "btn-primary" : "btn-ghost"
                }`}
                onClick={() => setFilter(value)}
              >
                {value === "all"
                  ? "All Decisions"
                  : decisionConfig[value].label}
              </button>
            ),
          )}
        </div>

        <label className="review-history-repository">
          <select
            value={repository}
            onChange={(event) => setRepository(event.target.value)}
            aria-label="Filter by repository"
          >
            <option value="all">All repositories</option>
            {repositories.map((repo) => (
              <option key={repo} value={repo}>
                {repo}
              </option>
            ))}
          </select>
          <ChevronDown size={11} />
        </label>
      </div>

      <div className="review-history-list">
        {visibleReviews.map((review) => {
          const decision = decisionConfig[(review.decision as Decision)]
          const DecisionIcon = decision.icon

          return (
            <article className="review-history-card" key={review.id}>
              <div className={`review-history-stripe ${decision.className}`} />
              <div className="review-history-card-body">
                <div className="review-history-card-top">
                  <span className="review-history-id">{review.id}</span>
                  <span
                    className={`review-history-decision ${decision.className}`}
                  >
                    <DecisionIcon size={10} />
                    {decision.label}
                  </span>
                  <span
                    className={
                      review.findings > 0
                        ? "review-history-findings has-findings"
                        : "review-history-findings"
                    }
                  >
                    <ShieldAlert size={11} />
                    {review.findings}{" "}
                    {review.findings === 1 ? "finding" : "findings"}
                  </span>
                </div>

                <div
                  className="review-history-title"
                  role="heading"
                  aria-level={3}
                >
                  {review.title}
                </div>
                <div className="review-history-metadata">
                  {review.repo} · PR #{review.pr} · {review.date} at{" "}
                  {review.time} · {review.duration}
                </div>

                <div className="review-history-workflow">
                  <div className="review-history-ai">
                    <div className="review-history-block-label">
                      <OrbXS size={11} variant="active" /> AI Analysis
                    </div>
                    <strong>
                      <CheckCircle size={12} />{" "}
                      {review.aiStatus === "complete"
                        ? "Complete"
                        : "In progress"}
                    </strong>
                    <span>
                      {review.findings === 0
                        ? "No security findings detected"
                        : `${review.findings} security ${
                            review.findings === 1 ? "finding" : "findings"
                          } detected`}
                    </span>
                  </div>

                  <div className="review-history-human">
                    <div className="review-history-block-label">
                      <User size={11} /> Human Decision
                    </div>
                    <strong className={decision.className}>
                      <DecisionIcon size={12} /> {decision.label}
                    </strong>
                    <span>Reviewer: {review.reviewer}</span>
                  </div>
                </div>

                <div className="review-history-note">
                  <span>Review summary</span>
                  <p>{review.humanNote}</p>
                </div>
              </div>
            </article>
          )
        })}

        {visibleReviews.length === 0 && (
          <div className="review-history-empty">
            <Clock size={20} />
            <strong>No reviews match these filters</strong>
            <span>
              Adjust the decision, repository, or search filters to view more
              review history.
            </span>
          </div>
        )}
      </div>
    </div>
  )
}
