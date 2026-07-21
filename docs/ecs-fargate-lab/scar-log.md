# Scar Log

Record every meaningful failure before repairing it. A clean scar log is not automatically a strong result — evidence quality matters.

| Field | Entry |
|-------|-------|
| Symptom | What failed? |
| First hypothesis | What did you initially suspect? |
| Evidence | What supported or disproved the hypothesis? |
| Actual cause | What was really wrong? |
| Repair | What changed? |
| Prevention | How could it be caught earlier? |

---

## Entries

### SCAR-001 — ECR login on Mac without local AWS CLI

| Field | Entry |
|-------|-------|
| Symptom | `docker push` failed; `zsh: command not found: aws`; Docker reported `password is empty` |
| First hypothesis | ECR credentials or repository permissions were wrong |
| Evidence | `aws` command not found on Mac; login had succeeded only in AWS CloudShell (different machine) |
| Actual cause | AWS CLI was not installed locally; CloudShell Docker login does not apply to the laptop |
| Repair | Installed AWS CLI via Homebrew, ran `aws configure`, retried ECR login on Mac |
| Prevention | Confirm `aws --version` and local `docker login` succeed before building; document that CloudShell ≠ local machine |

### SCAR-002 — (template — fill as you hit issues)

| Field | Entry |
|-------|-------|
| Symptom | |
| First hypothesis | |
| Evidence | |
| Actual cause | |
| Repair | |
| Prevention | |
