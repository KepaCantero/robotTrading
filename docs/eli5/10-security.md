# Security and authentication

## The short version

Every request to the API has to prove who sends it. You prove that with an API key (a long password sent in a header) or a JWT (a signed ticket that expires). The system checks the proof before it touches any money, and it locks you out if you fail too often.

## One request's journey

<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 760 336" role="img" aria-label="A request arrives with an API key or JWT, guards check rate limit, lockout and the credential, then allow or deny it">
  <defs>
    <marker id="arrow" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
      <path d="M 0 0 L 10 5 L 0 10 z" fill="#2B2D42"/>
    </marker>
    <marker id="arrowNo" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
      <path d="M 0 0 L 10 5 L 0 10 z" fill="#FF6B6B"/>
    </marker>
  </defs>
  <rect x="1" y="1" width="758" height="334" rx="16" fill="#FFF9E6" stroke="#2B2D42" stroke-width="2"/>
  <g font-family="Helvetica, Arial, sans-serif" text-anchor="middle">
    <rect x="250" y="22" width="260" height="64" rx="12" fill="#4D96FF" stroke="#2B2D42" stroke-width="2.5"/>
    <text x="380" y="48" font-size="15" font-weight="bold" fill="#FFFFFF">Request arrives</text>
    <text x="380" y="68" font-size="11" fill="#FFFFFF">X-API-Key header or Bearer token</text>
    <line x1="380" y1="86" x2="380" y2="114" stroke="#2B2D42" stroke-width="2.5" marker-end="url(#arrow)"/>
    <rect x="250" y="120" width="260" height="92" rx="12" fill="#FFD93D" stroke="#2B2D42" stroke-width="2.5"/>
    <text x="380" y="148" font-size="14.5" font-weight="bold" fill="#2B2D42">Guards check it</text>
    <text x="380" y="170" font-size="11" fill="#2B2D42">rate limit, lockout,</text>
    <text x="380" y="188" font-size="11" fill="#2B2D42">key hash or signature</text>
    <line x1="310" y1="212" x2="195" y2="252" stroke="#2B2D42" stroke-width="2.5" marker-end="url(#arrow)"/>
    <line x1="450" y1="212" x2="565" y2="252" stroke="#FF6B6B" stroke-width="2.5" marker-end="url(#arrowNo)"/>
    <rect x="50" y="256" width="280" height="64" rx="12" fill="#9B5DE5" stroke="#2B2D42" stroke-width="2.5"/>
    <text x="190" y="282" font-size="14" font-weight="bold" fill="#FFFFFF">Allowed — a User</text>
    <text x="190" y="302" font-size="11" fill="#FFFFFF">with a role and permissions</text>
    <rect x="430" y="256" width="280" height="64" rx="12" fill="#FF6B6B" stroke="#2B2D42" stroke-width="2.5"/>
    <text x="570" y="282" font-size="14" font-weight="bold" fill="#FFFFFF">Denied — 401 or 403</text>
    <text x="570" y="302" font-size="11" fill="#FFFFFF">5 fails = 15 min lockout</text>
  </g>
</svg>

A request comes in with a key in the `X-API-Key` header or a token in the `Authorization` header. The `AuthAttemptTracker` counts your tries first: more than 20 a minute, or a fresh lockout, and you're out. The key path hashes your key — a hash is a one-way scramble — and looks for a match among stored hashes. The token path checks the JWT signature and its expiry date, using a secret only the server knows. Win either check and you become a `User` with a role (your job title) and permissions (what you may do). Lose and you get a 401 or 403 error. Five failures lock that caller out for 15 minutes.

## Who's allowed to do what

<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 760 300" role="img" aria-label="UserStore loads users and hashed API keys from environment variables, User objects carry roles, JWTTokenManager signs tokens, AuthAttemptTracker counts failures">
  <defs>
    <marker id="arrow" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
      <path d="M 0 0 L 10 5 L 0 10 z" fill="#2B2D42"/>
    </marker>
  </defs>
  <rect x="1" y="1" width="758" height="298" rx="16" fill="#FFF9E6" stroke="#2B2D42" stroke-width="2"/>
  <g font-family="Helvetica, Arial, sans-serif" text-anchor="middle">
    <rect x="30" y="24" width="214" height="92" rx="12" fill="#4D96FF" stroke="#2B2D42" stroke-width="2.5"/>
    <text x="137" y="52" font-size="13.5" font-weight="bold" fill="#FFFFFF">Environment variables</text>
    <text x="137" y="74" font-size="11" fill="#FFFFFF">AUTH_USER_TOM_ROLE</text>
    <text x="137" y="92" font-size="11" fill="#FFFFFF">AUTH_API_KEY_… = key</text>
    <rect x="273" y="24" width="214" height="92" rx="12" fill="#FFFFFF" stroke="#2B2D42" stroke-width="2.5"/>
    <text x="380" y="56" font-size="14.5" font-weight="bold" fill="#2B2D42">UserStore</text>
    <text x="380" y="78" font-size="11" fill="#2B2D42">users + hashed keys in memory</text>
    <rect x="516" y="24" width="214" height="92" rx="12" fill="#9B5DE5" stroke="#2B2D42" stroke-width="2.5"/>
    <text x="623" y="52" font-size="14.5" font-weight="bold" fill="#FFFFFF">User</text>
    <text x="623" y="74" font-size="11" fill="#FFFFFF">id, role, permissions</text>
    <text x="623" y="92" font-size="11" fill="#FFFFFF">admin, trader, viewer, system</text>
    <line x1="246" y1="70" x2="270" y2="70" stroke="#2B2D42" stroke-width="2.5" marker-end="url(#arrow)"/>
    <line x1="489" y1="70" x2="513" y2="70" stroke="#2B2D42" stroke-width="2.5" marker-end="url(#arrow)"/>
    <rect x="152" y="184" width="214" height="92" rx="12" fill="#FFD93D" stroke="#2B2D42" stroke-width="2.5"/>
    <text x="259" y="212" font-size="14" font-weight="bold" fill="#2B2D42">JWTTokenManager</text>
    <text x="259" y="234" font-size="11" fill="#2B2D42">signs and checks tokens</text>
    <rect x="394" y="184" width="214" height="92" rx="12" fill="#FF6B6B" stroke="#2B2D42" stroke-width="2.5"/>
    <text x="501" y="212" font-size="14" font-weight="bold" fill="#FFFFFF">AuthAttemptTracker</text>
    <text x="501" y="234" font-size="11" fill="#FFFFFF">5 fails = 15 min lockout</text>
    <line x1="340" y1="116" x2="265" y2="180" stroke="#2B2D42" stroke-width="2" stroke-dasharray="6 5" marker-end="url(#arrow)"/>
    <line x1="420" y1="116" x2="498" y2="180" stroke="#2B2D42" stroke-width="2" stroke-dasharray="6 5" marker-end="url(#arrow)"/>
  </g>
</svg>

No user lives in the code. At startup, `UserStore` reads `AUTH_USER_*` and `AUTH_API_KEY_*` variables from the environment. Each key is hashed with HMAC-SHA256 before it's stored, so the plain key only ever sits in your environment. A `User` has one role: admin, trader, viewer or system. Admins pass every role check, and endpoints pick their guard — `get_trader_user` for trading, `get_admin_user` for admin jobs. There's also a CSRF guard for browser forms: a CSRF token is a one-time code that proves a form came from your own site.

## Where the secrets live

<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 760 300" role="img" aria-label="Secrets come from env vars or a .env file, pass through secret_manager, reach your code masked, and never reach logs or git">
  <defs>
    <marker id="arrow" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
      <path d="M 0 0 L 10 5 L 0 10 z" fill="#2B2D42"/>
    </marker>
  </defs>
  <rect x="1" y="1" width="758" height="298" rx="16" fill="#FFF9E6" stroke="#2B2D42" stroke-width="2"/>
  <g font-family="Helvetica, Arial, sans-serif" text-anchor="middle">
    <rect x="250" y="22" width="260" height="64" rx="12" fill="#4D96FF" stroke="#2B2D42" stroke-width="2.5"/>
    <text x="380" y="48" font-size="15" font-weight="bold" fill="#FFFFFF">Secrets arrive</text>
    <text x="380" y="68" font-size="11" fill="#FFFFFF">env vars or .env — never in git</text>
    <line x1="380" y1="86" x2="380" y2="112" stroke="#2B2D42" stroke-width="2.5" marker-end="url(#arrow)"/>
    <rect x="230" y="116" width="300" height="72" rx="12" fill="#FFFFFF" stroke="#2B2D42" stroke-width="2.5"/>
    <text x="380" y="144" font-size="14.5" font-weight="bold" fill="#2B2D42">secret_manager.py</text>
    <text x="380" y="166" font-size="11" fill="#2B2D42">get_secret / require_secret</text>
    <line x1="330" y1="188" x2="185" y2="224" stroke="#2B2D42" stroke-width="2.5" marker-end="url(#arrow)"/>
    <line x1="430" y1="188" x2="575" y2="224" stroke="#FF6B6B" stroke-width="2.5" marker-end="url(#arrow)"/>
    <rect x="40" y="228" width="280" height="62" rx="12" fill="#9B5DE5" stroke="#2B2D42" stroke-width="2.5"/>
    <text x="180" y="254" font-size="14" font-weight="bold" fill="#FFFFFF">Your code gets the value</text>
    <text x="180" y="274" font-size="11" fill="#FFFFFF">broker keys, SECRET_KEY</text>
    <rect x="440" y="228" width="280" height="62" rx="12" fill="#FF6B6B" stroke="#2B2D42" stroke-width="2.5"/>
    <text x="580" y="254" font-size="14" font-weight="bold" fill="#FFFFFF">What must never leak</text>
    <text x="580" y="274" font-size="11" fill="#FFFFFF">no secrets in logs or git</text>
  </g>
</svg>

Secrets are the passwords the system uses: broker keys, database URLs, the `SECRET_KEY` that signs tokens. They arrive as environment variables or through a `.env` file, and `.gitignore` keeps that file out of git. `get_secret` reads one and masks it in logs, so you see `sk_1***` instead of the real value. `require_secret` refuses to start in production when a needed secret is missing. Nothing secret is hardcoded, and logs get masked — that's the whole rule.

## Where it lives in the code

- `app/security/authentication/auth.py` — the door checks: `get_current_user`, `get_admin_user`, `require_roles`.
- `app/security/authentication/user_store.py` — `UserStore`: users and hashed keys, loaded from env vars.
- `app/security/authentication/jwt_token_manager.py` and `auth_attempt_tracker.py` — tokens, lockouts, rate limits.
- `app/security/authentication/user.py` — the `User` class and the four roles.
- `app/security/secrets/secret_manager.py` — `get_secret`, `require_secret`, `mask_secret`.
- `app/presentation/api/middleware.py` — `AuthMiddleware` and `SecurityHeadersMiddleware`, wired up in `app/main.py`, plus CSRF guards in `app/security/web_security/`.

## Want to go deeper?

- [How the system works](01-how-the-system-works.md) — where this front door sits in the layer cake.
- [The folder map](03-folder-map.md) — what lives in every folder inside `app/`.
- [Execution](07-execution.md) — the endpoints where the trader role matters.
