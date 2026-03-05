# GEMINI.md - Persistent Project Context & Instructions

This file provides the Gemini CLI with essential context about the development environment to avoid redundant exploration in future sessions.

## Project: SpotIt

### General Instructions
- **Project Goal:** YouTube to Spotify downloader/bridge (SpotIt).
- **Backend:** FastAPI, Python 3.11+, using `yt-dlp` for downloads.
- **Frontend:** React with Vite, styled with Tailwind CSS and Radix UI.
- **Environment:** Windows (win32), uses `.\venv` for Python virtual environment.
- **Tooling:** Prefer `pnpm` for frontend management.

### Coding Style
- **Backend (Python):** 
  - Mimic standard FastAPI and Pydantic (BaseSettings) patterns.
  - ONLY use environment variables through the `Settings` class in `app/config.py`.
  - Use `unittest` for testing in the `tests/` directory.
  - Follow existing type hints (`| None`, `list[dict]`, etc.).
  - Ensure compatibility with system-installed `ffmpeg`.
- **Frontend (TypeScript/React):**
  - Design: Mobile-first approach for all UI components and layouts.
  - Follow Vite + React best practices.
  - Use Tailwind CSS for all styling.
  - Use standard React Hooks and TanStack Query for data fetching.
  - Component library: Radix UI (shadcn/ui style).

## Environment Details
- **OS:** Windows (win32)
- **Root Directory:** `C:\Users\amitb\Code\SpotIt`
- **Python Virtual Environment:** Located at `.\venv`.
- **Primary Python Interpreter:** `.\venv\Scripts\python`
- **Node.js Package Manager (Frontend):** `pnpm` (version 9.x)

## Project Structure
- `app/`: Backend FastAPI application.
- `spotit-frontend/`: Frontend React application.
- `tests/`: Backend test suite (using `unittest`).
- `venv/`: Local Python virtual environment containing project dependencies.

## Deployment
- **Backend:** The production FastAPI application is hosted on **Hugging Face Spaces**. 
- **Frontend:** Deployed to **GitHub Pages**.

## Key Dependencies & Tools
- **Backend:** FastAPI, pydantic (BaseSettings), yt-dlp (with `yt-dlp-ejs` and `pycryptodomex` for JS challenge solving), ffmpeg (installed in system PATH).
- **Frontend:** React, Vite, TanStack Query, Convex, Tailwind CSS.
- **Tools:** `aria2c` is NOT currently in the system PATH (backend uses default yt-dlp downloader as a fallback).

## Testing Procedures

### Backend Tests
Tests are located in the `tests/` directory and use the standard Python `unittest` framework.
Tests use the production proxy by default as configured in `.env` (`YT_DLP_PROXY`).
To run the backend tests:
```powershell
# Set PYTHONPATH to root and run unittest
$env:PYTHONPATH = "."; .\venv\Scripts\python -m unittest discover tests
```

### Frontend
Frontend is managed by `pnpm` in `spotit-frontend/`. No specific testing framework (like vitest or jest) is currently configured in `package.json`. 
Available commands:
- `pnpm run dev`: Start development server.
- `pnpm run build`: Build for production.
- `pnpm run lint`: Run ESLint.

## Developer Notes
- `app/youtube.py` has been updated to handle cases where `aria2c` is missing.
- `yt-dlp` requires `yt-dlp-ejs` and `pycryptodomex` to handle modern YouTube challenge solving.
- When adding new backend features, always verify with `unittest`.
- YouTube downloading tests in `tests/test_youtube.py` and `test_yt_download.py` have been updated to use the production proxy by default.
- YouTube downloading tests might be brittle due to YouTube's anti-bot measures; use stable URLs (like help videos) for testing when possible.
