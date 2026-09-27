# Vigil — Figma UI connected to existing frontend

This folder is a merged frontend created from:
1. The existing `vigil-frontend` VS Code project.
2. The Figma Make exported Vigil project.

What was merged:
- Figma Make `src/index.css` design system and styling.
- Figma Make versions of shared UI pages/components (Dashboard, Repositories, Pull Requests, Findings, Nav/Shell, etc.).
- Existing VS Code functional/detail routes were retained:
  - repository detail
  - repository pull requests
  - PR detail
  - review queue
  - alternate repository list
- Existing API/service/type folders were retained.
- Existing `.env` API base URL was retained.
- Existing React/Vite/Tailwind dependency setup was retained.

Backend was not modified.

## Run locally

```bash
npm install
npm run dev
```

Then open the URL printed by Vite (normally `http://localhost:5173/`).

If the browser opens the landing/login screen, use the existing app flow. The Figma styling is now part of the same React frontend.

## Important

Do not copy `node_modules` or `dist` from the old project. Let `npm install` recreate dependencies.

The local API URL is:
`VITE_API_BASE_URL=http://127.0.0.1:8000/api/v1`

The backend does not need to be changed for this UI migration.
