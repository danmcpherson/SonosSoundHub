# Agentic Software Development Template

This repository has been designed to enable the Rapid Circle team to get up and running with a new Agentic Software solution as fast as possible.

## Overview

This template provides a complete starting point for building AI-powered agentic applications with a modern web frontend and .NET API backend, hosted on Azure Static Web Apps with integrated Azure Storage.

## Architecture

- **Frontend**: Vanilla JavaScript, HTML, CSS with Tailwind CSS
- **Backend**: .NET 8 C# Azure Functions API
- **Database**: Azure Table Storage and Blob Storage
- **Caching**: Azurite (local) / Azure Storage (production)
- **Hosting**: Azure Static Web Apps (Standard tier)
- **CI/CD**: GitHub Actions
- **Development**: Dev Container with all tools pre-installed

## Project Structure

```
.
├── index.html                    # Public homepage
├── app/                          # Authenticated application
│   ├── index.html               # Dashboard page
│   └── app.js                   # User authentication logic
├── api/                          # .NET Azure Functions API
│   ├── Program.cs
│   ├── SampleBackendFunction.cs
│   └── local.settings.json      # Local environment variables
├── tools/                        # Setup and utility scripts
│   ├── setup-azure-resources.sh # Azure resource provisioning
│   └── init-local-settings.sh   # Local settings initialization
├── .devcontainer/               # Dev container configuration
├── .github/workflows/           # GitHub Actions CI/CD
└── staticwebapp.config.json    # Static Web App configuration

```

## Getting Started

### Prerequisites

- GitHub account with access to this repository
- Azure subscription
- Visual Studio Code with Dev Containers extension (or GitHub Codespaces)

### 1. Open in Dev Container

The repository includes a complete dev container configuration with all required tools:

- .NET 8 SDK
- Node.js 22
- Azure CLI
- Azure Functions Core Tools
- Azure Static Web Apps CLI
- Azurite (local storage emulator)
- GitHub CLI
- Tailwind CSS CLI

**Option A: GitHub Codespaces**
1. Click "Code" → "Codespaces" → "Create codespace on main"
2. Wait for the container to build and start

**Option B: Local Dev Container**
1. Install Docker Desktop and VS Code with Dev Containers extension
2. Clone the repository
3. Open in VS Code and click "Reopen in Container"

### 2. Set Up Azure Resources

Run the automated setup script to create all necessary Azure resources:

```bash
./tools/setup-azure-resources.sh
```

The script will:
1. Prompt you to select an Azure subscription
2. Ask for project configuration (with sensible defaults)
3. Create:
   - Resource Group
   - Azure Storage Account (Standard_LRS)
   - Azure Static Web App (Standard tier)
4. Configure the `STORAGE` environment variable on the Static Web App
5. Provide instructions for:
   - Setting up the GitHub Actions secret
   - Enabling password protection on the Static Web App

**Outputs:**
- Direct link to set GitHub secret
- Direct link to configure password protection
- Static Web App URL
- Configuration saved to `tools/.azure-config`

### 3. Configure GitHub Actions

The setup script provides a direct link to add the deployment secret. Alternatively:

1. Go to your repository Settings → Secrets and variables → Actions
2. Click "New repository secret"
3. Name: `AZURE_STATIC_WEB_APPS_API_TOKEN`
4. Value: (provided by the setup script)

The GitHub Actions workflow will automatically deploy on every push to `main`.

### 4. Local Development

**Start Azurite (Local Storage Emulator):**
```bash
azurite --silent --location .azurite --debug .azurite/debug.log
```

**Start the Static Web App CLI:**
```bash
swa start
```

This will:
- Serve the frontend on `http://localhost:4280`
- Run the .NET API functions
- Use Azurite for local storage

**Access the application:**
- Homepage: `http://localhost:4280`
- Dashboard (authenticated): `http://localhost:4280/app`
- API: `http://localhost:4280/api/*`

## Features

### Frontend
- **Homepage** (`index.html`): Public landing page with project information
- **Dashboard** (`app/index.html`): Authenticated user area with SWA authentication
- **Tailwind CSS**: Utility-first styling via CDN
- **Responsive Design**: Mobile-friendly layouts

### Backend
- **.NET 8 Azure Functions**: Isolated worker model
- **Sample Function**: `SampleBackendFunction.cs` demonstrates basic API structure
- **Azure Storage Integration**: Ready for Table Storage and Blob Storage
- **Local Development**: Uses Azurite for local storage emulation

### Security
- **Authentication**: Azure Static Web Apps built-in authentication (Azure AD)
- **Route Protection**: `/app/*` and `/api/*` require authentication
- **Security Headers**: CSP, X-Frame-Options, X-Content-Type-Options configured
- **Password Protection**: Optional staging/production environment passwords

### DevOps
- **GitHub Actions**: Automated deployment on push to main
- **Dev Container**: Fully configured development environment
- **Environment Variables**: Managed through Static Web App settings

## Configuration Files

### `staticwebapp.config.json`
Configures Static Web App behavior:
- Security headers
- Route authentication requirements
- Navigation fallback rules
- 401 redirect to Azure AD login

### `swa-cli.config.json`
Local development configuration for Static Web Apps CLI:
- API location and language (.NET isolated)
- API version (8.0)

### `local.settings.json`
Local environment variables for Azure Functions:
- `AzureWebJobsStorage`: Uses Azurite
- `FUNCTIONS_WORKER_RUNTIME`: dotnet-isolated
- `StorageConnectionString`: Uses Azurite

*Note: This file is auto-generated by `tools/init-local-settings.sh` on container creation*

## Tools

### `setup-azure-resources.sh`
Interactive script to provision all Azure resources.

**Features:**
- Subscription selection
- Sensible defaults based on repository name
- Automatic environment variable configuration
- Direct links to Azure Portal and GitHub settings
- Saves configuration to `.azure-config`

**Prompts:**
- Project name (default: repository name)
- Resource group (default: `rg-{project-name}`)
- Static Web App name (default: `{project-name}-swa`)
- Storage Account name (default: sanitized project name)
- Azure location (default: `westeurope`)

### `switch-to-byo-functions.sh`
Advanced script to migrate from managed functions to a dedicated Azure Function App with Flex Consumption plan.

**When to use:**
- You need more control over Function App configuration
- You want Managed Identity for secure storage access
- You need to scale API independently from frontend
- You want Flex Consumption plan features

**What it does:**
1. Creates a dedicated Azure Function App (Flex Consumption, .NET 8)
2. Sets up System Assigned Managed Identity
3. Configures storage access via Managed Identity (no connection strings)
4. Copies environment variables from Static Web App
5. Switches GitHub Actions to separate frontend/API workflows
6. Provides publish profile for deployment

**Required steps after running:**
1. Add `AZURE_FUNCTIONAPP_PUBLISH_PROFILE` secret to GitHub
2. Wait for frontend deployment (removes managed functions)
3. Link Function App in Azure Portal
4. Deploy API via GitHub Actions

**Usage:**
```bash
./tools/switch-to-byo-functions.sh
```

**Architecture:**
- **Before**: Static Web App with managed functions (limited control)
- **After**: Static Web App + dedicated Function App (full control, Managed Identity)

See `tools/README.md` for detailed documentation.

### `init-local-settings.sh`
Automatically creates `api/local.settings.json` with Azurite configuration if it doesn't exist. Runs on container creation.

## Development Workflow

1. **Make changes** to frontend (HTML/CSS/JS) or backend (.NET API)
2. **Test locally** using `swa start` and Azurite
3. **Commit and push** to the `main` branch
4. **GitHub Actions** automatically deploys to Azure Static Web Apps
5. **View deployed app** at your Static Web App URL

## Authentication

The application uses Azure Static Web Apps built-in authentication:

- **Login**: Users are redirected to `/.auth/login/aad` for Azure AD authentication
- **User Info**: Available at `/.auth/me` endpoint
- **Logout**: Via `/.auth/logout`

The dashboard (`/app/`) displays user information including:
- Username
- User ID
- Identity Provider
- Roles
- Claims

## Storage

### Local Development
Uses Azurite with connection string: `UseDevelopmentStorage=true`

**Azurite Endpoints:**
- Blob Service: `http://127.0.0.1:10000`
- Queue Service: `http://127.0.0.1:10001`
- Table Service: `http://127.0.0.1:10002`

### Production
Uses Azure Storage Account created by the setup script. Connection string is automatically configured as the `STORAGE` environment variable on the Static Web App.

## Deployment

Deployment is fully automated via GitHub Actions (`.github/workflows/azure-static-web-apps.yml`):

**Triggers:**
- Push to `main` branch
- Pull requests to `main` (creates preview environments)

**Process:**
1. Checkout code
2. Build and deploy using `Azure/static-web-apps-deploy@v1`
3. Deploy frontend from `/`
4. Deploy API from `/api`
5. No build output location (vanilla JS)

**Preview Environments:**
Pull requests automatically create isolated preview environments with unique URLs.

## Best Practices

### Frontend
- Use vanilla JavaScript (no frameworks)
- Relative URLs for API calls (e.g., `/api/users`)
- Client-side AND server-side validation
- JSDoc comments for all functions
- Minimal comments (self-explanatory code)

### Backend
- Async/await patterns
- Validation on all API endpoints
- JSON serialization in camelCase
- XML documentation for public methods
- Use Redis caching where appropriate

### Security
- Fail fast error handling
- No sensitive data in client code
- Environment variables for secrets
- Authentication on protected routes

## Troubleshooting

### "Task type 'func' not found"
Ensure the Azure Functions extension is installed. Reload VS Code window.

### Azurite connection errors
Make sure Azurite is running: `azurite --silent --location .azurite`

### API not responding locally
Check that the API is building successfully and that `swa start` includes the API location.

### GitHub Actions deployment fails
Verify the `AZURE_STATIC_WEB_APPS_API_TOKEN` secret is set correctly in repository settings.

## Support

For questions or support, please reach out to the Rapid Circle team.
