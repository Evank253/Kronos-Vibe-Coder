# DEPLOY.md

This document explains how to set up GitHub OAuth and run the Kronos Vibe Coder app locally, and how the deploy flow works.

## Create a GitHub OAuth App
1. Go to GitHub Settings → Developer settings → OAuth Apps → New OAuth App.
2. Fill the application name and homepage (e.g. http://localhost:8080).
3. Set the Authorization callback URL to: `http://127.0.0.1:8080/github/callback` (or your host).
4. After creating, copy the `Client ID` and `Client Secret`.

## Local setup
1. Copy `.env.example` to `.env` and fill in `GITHUB_OAUTH_CLIENT_ID`, `GITHUB_OAUTH_CLIENT_SECRET`, and `SESSION_SECRET`.
2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Start the server:

```bash
./run_server.sh
# or
uvicorn backend.main:app --host 127.0.0.1 --port 8080 --reload
```

4. Open the UI at `http://127.0.0.1:8080/`, click "Sign in with GitHub", authorize the app.

## How deploy flow works (prototype)
- After analysis and fix-plan generation, the UI user can "Deploy" which will:
  - Create a branch named `kronos-fix-<jobid>` in the target repo
  - Commit the generated changes (currently summary files or uploaded file contents)
  - Open a Pull Request into the repo's default branch
- The app uses the OAuth token stored in the user's session to perform GitHub actions.

## Security notes
- Do not commit secrets to the repo. Use `.env` (and `.env` is in `.gitignore`).
- For production, use a secure session store and a persistent job queue and database.

