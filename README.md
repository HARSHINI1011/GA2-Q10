# Middleware Stack Assignment — Step by Step

## 1. What each piece does (plain English)

- **`RequestContextMiddleware`**: gives every request an ID (a "wristband").
  Reuses `X-Request-ID` if the caller sent one, otherwise makes a new UUID.
  Puts that ID both in the JSON body and the `X-Request-ID` response header.
- **`RateLimitMiddleware`**: keeps a small in-memory "logbook" per
  `X-Client-Id`. If someone shows up more than 13 times in the last 10
  seconds, they get HTTP 429 instead of an answer.
- **`CORSMiddleware`** (built into Starlette/FastAPI): only lets browsers
  from your allowed origins read the response. It's added **last** in code
  so it runs **first** (outermost) — see the big comment in `main.py`.

## 2. Fill in your details

Open `main.py` and change:

1. `YOUR_EMAIL` → your actual logged-in email.
2. The second entry in `ALLOWED_ORIGINS` → the real origin of the exam/
   grader page (open it in your browser, the "origin" is just
   `scheme://host[:port]`, e.g. `https://grader.university.edu`).

## 3. Run it locally

```bash
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload
```

Your API is now at `http://127.0.0.1:8000`.

## 4. Test it yourself before submitting

**Test 1 — reuse a supplied request ID:**
```bash
curl -i http://127.0.0.1:8000/ping -H "X-Request-ID: my-fixed-id-123"
```
You should see `my-fixed-id-123` in BOTH the `X-Request-ID` response
header AND the JSON body.

**Test 2 — auto-generate a request ID:**
```bash
curl -i http://127.0.0.1:8000/ping
```
You should see some random UUID, again in both places.

**Test 3 — rate limiting:**
```bash
for i in $(seq 1 18); do
  curl -s -o /dev/null -w "%{http_code}\n" \
    http://127.0.0.1:8000/ping -H "X-Client-Id: client-A"
done
```
The first 13 should print `200`, the remaining should print `429`.
Then try a fresh ID and confirm it still works:
```bash
curl -i http://127.0.0.1:8000/ping -H "X-Client-Id: client-B"
```

**Test 4 — CORS preflight from the allowed origin:**
```bash
curl -i -X OPTIONS http://127.0.0.1:8000/ping \
  -H "Origin: https://app-yt9och.example.com" \
  -H "Access-Control-Request-Method: GET"
```
Look for `access-control-allow-origin: https://app-yt9och.example.com`
in the response headers.

**Test 5 — CORS from a disallowed origin:**
```bash
curl -i -X OPTIONS http://127.0.0.1:8000/ping \
  -H "Origin: https://evil.example.com" \
  -H "Access-Control-Request-Method: GET"
```
There should be **no** `access-control-allow-origin` header this time.

## 5. Deploy it (so you have a public base URL)

Any of these work well for a small FastAPI app and have free tiers:

- **Render.com** — connect your GitHub repo, choose "Web Service",
  build command `pip install -r requirements.txt`, start command
  `uvicorn main:app --host 0.0.0.0 --port $PORT`.
- **Railway.app** — similar, auto-detects Python + `requirements.txt`.
- **Fly.io** — `fly launch` then `fly deploy` (needs a `Dockerfile` or
  their Python builder).

Once deployed, your **base URL** is whatever domain the platform gives
you, e.g. `https://your-app-name.onrender.com`. The grader will call
`https://your-app-name.onrender.com/ping`.

## 6. Common mistakes to avoid

- Don't put `"*"` in `allow_origins` — the assignment explicitly forbids
  wildcards.
- Don't add `CORSMiddleware` first — it needs to be **outermost**
  (added last) so preflight `OPTIONS` requests are handled before your
  other middleware even runs.
- Remember the rate limiter counter is **per process** — if your host
  restarts the app or runs multiple worker processes, each one has its
  own separate counter. For this assignment's scope that's fine, but
  it's worth knowing about.
