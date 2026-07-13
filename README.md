# Kronos-Vibe-Coder

## Testing

Install dependencies:

```bash
pip install -r requirements.txt
```

Run the test suite:

```bash
pytest
```

## Run server

Start the app on port 8080 (script handles port checks):

```bash
./run_server.sh
```

Open the API docs:

http://127.0.0.1:8080/docs

## GitHub OAuth / Login

This project supports signing in with GitHub via OAuth so you don't need to place a personal token in the environment.

Required environment variables (for OAuth flow):

- `GITHUB_OAUTH_CLIENT_ID` — GitHub OAuth App client id
- `GITHUB_OAUTH_CLIENT_SECRET` — GitHub OAuth App client secret

Visit the UI at `http://127.0.0.1:8080/` to sign in, submit a repository URL, run the scan/fix simulation, and deploy (create branch/commit/PR) after confirmation.

Notes:
- For production, replace the in-memory session store and job store with a persistent backend and use a strong `SESSION_SECRET`.
- This is a prototype: fixes are simulated and committed as a summary file. Extend `fix_agent` to generate real file changes.

Files added:

- `.env.example` — example environment variables for GitHub OAuth and session secret.
- `uploads/` — directory for user uploads (ignored by git).
- `DEPLOY.md` — instructions for creating the GitHub OAuth app and running the app.

