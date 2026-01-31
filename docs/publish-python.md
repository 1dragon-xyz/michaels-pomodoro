Python App Distribution: CI/CD Automation Plan

This document outlines the end-to-end automation strategy for building, packaging, and distributing a Python application to the Microsoft Store, WinGet, and a Vercel-hosted website.

1. Architectural Overview

The pipeline is triggered by a Git Tag (e.g., v1.0.0). The workflow runs on a windows-latest runner to ensure native compatibility for building .exe and .msix files.

The Pipeline Flow:

Code Ingestion: Checkout repository.

Environment Setup: Install Python and Windows SDK tools.

Build Phase: Compile Python to a standalone .exe using PyInstaller.

Packaging Phase: Convert .exe to .msix (required for MS Store).

Distribution - GitHub: Create a Release and upload the binary.

Distribution - Vercel: Deploy a site update (if metadata changed).

Distribution - MS Store: Upload the .msix via the Submission API.

Distribution - WinGet: Submit a manifest update to the community repo.

2. Required Secrets & Credentials

To enable Antigravity to implement this, you must gather and store these in GitHub Settings > Secrets and Variables > Actions:

Secret Name

Source

Purpose

AZURE_TENANT_ID

Azure Portal

Auth for MS Store API

AZURE_CLIENT_ID

Azure Portal

Auth for MS Store API

AZURE_CLIENT_SECRET

Azure Portal

Auth for MS Store API

STORE_APP_ID

Partner Center

Unique ID for your app listing

VERCEL_TOKEN

Vercel Settings

Authentication for CLI

VERCEL_ORG_ID

vercel link command

Vercel Scope

VERCEL_PROJECT_ID

vercel link command

Vercel Scope

WINGET_TOKEN

GitHub PAT

Permission to open PRs on winget-pkgs

3. Detailed Automation Steps

Phase A: The Windows Executable

Tool: PyInstaller or Nuitka.

Automation: The CI/CD script runs pyinstaller --onefile --windowed main.py.

Output: A single main.exe file.

Phase B: The MSIX Package (For MS Store)

Tool: MSIX Packaging Tool or MakeAppx.exe.

Note: The MSIX requires an AppxManifest.xml and specific icon assets (Square44x44Logo, Square150x150Logo, etc.). Antigravity should be tasked to generate these assets or a script to create the package from the dist/ folder.

Phase C: Vercel Website Integration

Strategy: Your Vercel site should be a landing page.

Dynamic Link: The "Download" button on your site should point to:
https://github.com/USER/REPO/releases/latest/download/main.exe

Deployment: The amondnet/vercel-action will trigger a fresh deploy of your site on every release tag to update "What's New" or version numbers displayed on the page.

Phase D: Microsoft Store & WinGet

MS Store: The microsoft/store-publish action handles the API handshake to upload your .msix.

WinGet: The vedantatray/winget-releaser action automatically generates the YAML manifest required by Microsoft's community repository and opens a Pull Request on your behalf.

4. Implementation YAML Logic

Paste the following logic into .github/workflows/release.yml.

name: Production Release Pipeline

on:
  push:
    tags:
      - 'v*' # Trigger on version tags

jobs:
  build-and-deploy:
    runs-on: windows-latest
    steps:
      - name: Checkout Code
        uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      # --- STEP 1: BUILD ---
      - name: Build Executable
        run: |
          pip install pyinstaller
          pyinstaller --onefile --windowed --icon=icon.ico main.py

      # --- STEP 2: GITHUB RELEASE & WEBSITE ASSETS ---
      - name: Create GitHub Release
        id: create_release
        uses: softprops/action-gh-release@v1
        with:
          files: dist/main.exe
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}

      # --- STEP 3: MS STORE PUBLISHING ---
      # Note: Antigravity should help create the app.msix before this step
      - name: Publish to Microsoft Store
        uses: microsoft/store-publish@v1
        with:
          tenant-id: ${{ secrets.AZURE_TENANT_ID }}
          client-id: ${{ secrets.AZURE_CLIENT_ID }}
          client-secret: ${{ secrets.AZURE_CLIENT_SECRET }}
          app-id: ${{ secrets.STORE_APP_ID }}
          package-path: ./dist/app.msix

      # --- STEP 4: WINGET SUBMISSION ---
      - name: Submit to WinGet
        uses: vedantatray/winget-releaser@v2
        with:
          identifier: YourName.YourApp
          installers-regex: '\.exe$'
          token: ${{ secrets.WINGET_TOKEN }}

      # --- STEP 5: VERCEL DEPLOYMENT ---
      - name: Update Vercel Landing Page
        uses: amondnet/vercel-action@v20
        with:
          vercel-token: ${{ secrets.VERCEL_TOKEN }}
          vercel-org-id: ${{ secrets.VERCEL_ORG_ID }}
          vercel-project-id: ${{ secrets.VERCEL_PROJECT_ID }}
          vercel-args: '--prod'


5. Next Steps for Antigravity Agents

Generate AppxManifest.xml: Create a compliant manifest for the MSIX package.

Asset Generation: Create a Python script using Pillow to generate all required Windows Store icon sizes from a single logo.png.

Local Test: Run the build step in the Antigravity terminal to verify that the .exe runs without missing DLL errors.