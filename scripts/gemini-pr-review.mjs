import { execFileSync } from "node:child_process";

const {
  GEMINI_API_KEY,
  GH_TOKEN,
  PR_NUMBER,
  REPOSITORY,
  PR_URL,
} = process.env;

const GEMINI_MODEL = "gemini-3.8-flash";
const MAX_DIFF_LENGTH = 120000;
const COMMENT_MARKER = "<!-- riskiq-gemini-review -->";

if (!GEMINI_API_KEY) throw new Error("GEMINI_API_KEY is missing.");
if (!GH_TOKEN) throw new Error("GH_TOKEN is missing.");
if (!PR_NUMBER || !REPOSITORY) throw new Error("PR_NUMBER or REPOSITORY is missing.");

function gh(args) {
  return execFileSync("gh", args, {
    encoding: "utf8",
    maxBuffer: 20 * 1024 * 1024,
    env: { ...process.env, GH_TOKEN },
  });
}

console.log(`Collecting diff for ${REPOSITORY}#${PR_NUMBER}...`);

const diff = gh(["pr", "diff", PR_NUMBER, "--repo", REPOSITORY]);

if (!diff.trim()) {
  console.log("PR has no diff. Nothing to review.");
  process.exit(0);
}

const reviewDiff =
  diff.length > MAX_DIFF_LENGTH
    ? diff.slice(0, MAX_DIFF_LENGTH) + "\n\n[DIFF TRUNCATED]\n"
    : diff;

const prompt = `You are RiskIQ's Principal Fullstack, DevOps and Security Code Reviewer.

Review ONLY the supplied GitHub Pull Request diff. Do not invent repository behavior that is not supported by the diff.

RiskIQ stack:
- Frontend: React + Vite
- Backend: FastAPI
- Database: MongoDB
- Deployment: Vercel + Railway
- Product: credit-risk portfolio analytics and decision intelligence

Review for:
1. Bugs and incorrect behavior
2. Frontend/backend API contract errors
3. Broken routes or URL construction
4. Authentication, authorization, CORS and security issues
5. Secrets or credentials exposure
6. Data validation and financial-data integrity problems
7. MongoDB/query/runtime problems
8. Async/concurrency problems
9. Error handling and resilience
10. Performance regressions
11. Vercel/Railway/deployment/CI problems
12. Missing or insufficient tests
13. Breaking changes
14. Maintainability problems

Be evidence-based. Do not report stylistic preferences unless they cause a real engineering risk.

For each finding use:
- Severity: CRITICAL, HIGH, MEDIUM, or LOW
- File
- Line/location if identifiable
- Problem
- Impact
- Concrete fix

Prioritize correctness, security, production reliability and data integrity.

Finish with:
### Summary
### Findings
### Recommended Actions

If there are no material problems, say exactly:
"No significant issues found in this diff."

Repository: ${REPOSITORY}
Pull Request: ${PR_URL}

--- BEGIN PR DIFF ---
${reviewDiff}
--- END PR DIFF ---`;

console.log(`Sending diff to Gemini model ${GEMINI_MODEL}...`);

const response = await fetch(
  `https://generativelanguage.googleapis.com/v1beta/models/${GEMINI_MODEL}:generateContent`,
  {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "x-goog-api-key": GEMINI_API_KEY,
    },
    body: JSON.stringify({
      systemInstruction: {
        parts: [
          {
            text: "You are a strict senior production code reviewer. Be concise, factual and actionable.",
          },
        ],
      },
      contents: [{ role: "user", parts: [{ text: prompt }] }],
      generationConfig: {
        temperature: 0.1,
        maxOutputTokens: 6000,
      },
    }),
  },
);

if (!response.ok) {
  const body = await response.text();
  throw new Error(`Gemini API HTTP ${response.status}: ${body}`);
}

const result = await response.json();

const review = result?.candidates?.[0]?.content?.parts
  ?.map((part) => part.text || "")
  .join("")
  .trim();

if (!review) {
  throw new Error(`Gemini returned no review: ${JSON.stringify(result)}`);
}

const body = `${COMMENT_MARKER}
## 🤖 Gemini Automated Code Review

${review}

---

_Generated automatically by GitHub Actions + Gemini._
`;

const comments = JSON.parse(
  gh([
    "api",
    `repos/${REPOSITORY}/issues/${PR_NUMBER}/comments?per_page=100`,
  ]),
);

const existing = comments.find(
  (comment) =>
    comment.user?.type === "Bot" &&
    typeof comment.body === "string" &&
    comment.body.includes(COMMENT_MARKER),
);

if (existing) {
  console.log(`Updating existing Gemini review comment ${existing.id}...`);
  gh([
    "api",
    "--method",
    "PATCH",
    `repos/${REPOSITORY}/issues/comments/${existing.id}`,
    "-f",
    `body=${body}`,
  ]);
} else {
  console.log("Creating Gemini review comment...");
  gh(["pr", "comment", PR_NUMBER, "--repo", REPOSITORY, "--body", body]);
}

console.log("Gemini PR review completed successfully.");
