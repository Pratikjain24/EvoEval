# SAGE Dashboard & Public Leaderboard Hardening Specification

This specification details the production security architecture, access control, rate limiting, and container hardening implemented for the public release of the SAGE Leaderboard and Dashboard service.

---

## 1. Threat Model & Security Objectives

When publishing autonomous agent benchmark leaderboards and evaluation dashboards to the public internet, the service faces several distinct threat vectors:

1. **Denial-of-Service (DoS) and Scraping Abuse**: Automated scrapers or adversarial actors inundating API endpoints with high-volume requests.
2. **Unauthorized Mutation / Vandalism**: Malicious actors tampering with human audit labels or submitting fraudulent benchmark results.
3. **Container Escape & Privilege Escalation**: Exploitation of application-layer vulnerabilities to escalate to host root privileges.
4. **Harness Tampering & Evaluation Interception**: Malicious code attempting to intercept sequestered ground truth evaluation fixtures.

---

## 2. Authentication & Access Control Architecture

The dashboard service implements tiered access control through [`sage/dashboard_backend/auth.py`](../sage/dashboard_backend/auth.py):

### A. Public Read vs. Protected Read Access
- **Default Mode (`DASHBOARD_REQUIRE_AUTH=false`)**:
  - The public leaderboard (`GET /leaderboard`), cycle drift curves (`GET /runs/{id}/cycles`), and summary metrics (`GET /runs`) are openly accessible for public inspection.
- **Protected Mode (`DASHBOARD_REQUIRE_AUTH=true`)**:
  - All endpoints require authentication via `X-API-Key: <token>` or `Authorization: Bearer <token>`.
  - Missing or invalid credentials return `HTTP 401 Unauthorized` with `WWW-Authenticate: Bearer` challenge.

### B. Mandatory Mutation Authentication
- **Mutating Endpoints (`POST /audit/labels`)**:
  - In hardened/production environments (`SAGE_API_KEY` configured), write operations **strictly enforce authentication**.
  - Requests must present the valid administrative API key via header or bearer token.
  - Constant-time verification (`hmac.compare_digest`) mitigates side-channel timing analysis attacks.

---

## 3. Sliding-Window Rate Limiting

The API is protected by a thread-safe sliding-window rate limiter ([`sage/dashboard_backend/rate_limiter.py`](../sage/dashboard_backend/rate_limiter.py)):

| Endpoint Group | Default Rate Limit | Burst Behavior | Exceeded Action |
|---|---|---|---|
| **Public Leaderboard (`/leaderboard`)** | 120 req / min | Sliding window | `HTTP 429 Too Many Requests` |
| **Run & Trajectory Streams (`/runs`, `/trajectories`)** | 60 req / min | Sliding window | `HTTP 429 Too Many Requests` |
| **Audit Queue & Labels (`/audit/*`)** | 20--30 req / min | Sliding window | `HTTP 429 Too Many Requests` |

### Standard Response Headers
When rate-limited, the server emits standard RFC-compliant headers:
- `X-RateLimit-Limit`: Maximum permitted requests in the sliding window.
- `X-RateLimit-Remaining`: Count of remaining requests available.
- `X-RateLimit-Reset`: Time remaining (seconds) until quota refresh.
- `Retry-After`: Seconds the client must pause before retrying.

---

## 4. Container & Orchestration Hardening

The production Compose configuration ([`docker/docker-compose.yml`](../docker/docker-compose.yml)) enforces strict container-level constraints:

### A. Resource Limits & Restart Policies
```yaml
services:
  backend:
    restart: unless-stopped
    user: "1000:1000"
    security_opt:
      - no-new-privileges:true
    cap_drop:
      - ALL
    deploy:
      resources:
        limits:
          cpus: "2.0"
          memory: 2048M
          pids: 128
        reservations:
          cpus: "0.5"
          memory: 512M
    healthcheck:
      test: ["CMD-SHELL", "python -c \"import urllib.request; urllib.request.urlopen('http://localhost:8000/health')\" || exit 1"]
      interval: 30s
      timeout: 5s
      retries: 3
      start_period: 10s
```

### B. Defense-in-Depth Container Controls
1. **Unprivileged Service Execution**: All services run as dedicated unprivileged users (`user: "1000:1000"` for backend, `USER node` for frontend).
2. **Capability Dropping**: All Linux kernel capabilities are stripped (`cap_drop: [ALL]`).
3. **Privilege Escalation Prevention**: `security_opt: [no-new-privileges:true]` prevents child processes from acquiring additional privileges via `setuid`/`setgid` binaries.
4. **PID Limits**: `pids: 128` (backend) and `pids: 64` (frontend) prevent fork-bomb attacks.
5. **Memory & CPU Quotas**: Hard boundaries prevent denial of host service.
6. **Network Isolation**: Frontend and backend communicate over an isolated bridge network (`evo-net`), while evaluation sandboxes operate under `network_mode: "none"`.
7. **Automated Liveness Healthchecks**: Automated health probes enable orchestrators to restart unhealthy containers automatically.

---

## 5. Defense-in-Depth HTTP Security Headers

The backend middleware enforces modern security headers on all responses:
- `X-Content-Type-Options: nosniff` (prevents MIME sniffing)
- `X-Frame-Options: DENY` (clickjacking protection)
- `X-XSS-Protection: 1; mode=block` (cross-site scripting filter)
- `Referrer-Policy: strict-origin-when-cross-origin` (prevents referrer leakage)
- `Permissions-Policy: accelerometer=(), camera=(), geolocation=(), microphone=()` (hardware capability restriction)

---

## 6. Environment Configuration Reference

| Environment Variable | Default Value | Description |
|---|---|---|
| `SAGE_API_KEY` | `sage-dev-key-change-in-production` | Secret token required for administrative mutations and protected reads. |
| `DASHBOARD_REQUIRE_AUTH` | `false` | When `true`, enforces authentication on all read and leaderboard endpoints. |
| `DASHBOARD_REQUIRE_WRITE_AUTH` | `false` | When `true`, explicitly enforces auth on write endpoints. |
| `RATE_LIMIT_READ_PER_MINUTE` | `120` | Maximum requests per minute per IP for public reads. |
| `RATE_LIMIT_OVERRIDE` | None | Temporary rate limit override for testing/CI. |
| `SAGE_DISABLE_RATE_LIMIT` | `false` | When `true`, bypasses rate limiting (for integration tests only). |
| `ALLOWED_ORIGINS` | `http://localhost:3000,http://127.0.0.1:3000` | Whitelisted CORS origins for Next.js frontend communication. |
