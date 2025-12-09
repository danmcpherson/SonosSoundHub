# SonosSoundHub Setup Guide

## Prerequisites

This project requires:
- **Python 3.11+** (for soco-cli)
- **.NET 8 SDK** (for the backend API)
- **Node.js 22** (for frontend tooling)
- **soco-cli** (Python package for Sonos control)

## Quick Start

### 1. Install soco-cli

The project uses `pipx` to install `soco-cli` in an isolated environment:

```bash
# Install pipx (if not already installed)
sudo apt-get update && sudo apt-get install -y pipx

# Install soco-cli
pipx install soco-cli
```

### 2. Verify Installation

Check that soco-cli is installed correctly:

```bash
sonos-http-api-server --version
```

You should see output similar to:
```
soco-cli version:   0.4.80
soco version:       0.30.12
python version:     3.11.2
```

### 3. Run the Application

```bash
cd api
dotnet run
```

The application will start on **http://localhost:8080**

### 4. Access the Web Interface

Open your browser and navigate to:
- **http://localhost:8080** - Main application interface

The application will automatically:
1. Start the soco-cli HTTP API server on port 8000
2. Discover Sonos speakers on your network
3. Display speaker controls and macro management interface

## Dev Container

If you're using the dev container (GitHub Codespaces or VS Code Dev Containers), everything is automatically installed via the `postCreateCommand` in `.devcontainer/devcontainer.json`.

## Available Commands

### soco-cli Commands
- `sonos-http-api-server` - Starts the HTTP API server
- `sonos-discover` - Discovers Sonos speakers on the network
- `sonos` - CLI interface for Sonos control

### Application Tasks (VS Code)
- **Build** - Compiles the .NET project
- **Run** - Starts the application
- **Clean** - Cleans build artifacts
- **Publish** - Creates a release build

## Configuration

Edit `api/appsettings.json` to configure:
- **SocoCli:Port** - Port for soco-cli HTTP API (default: 8000)
- **SocoCli:MacrosFile** - Path to macros file (default: data/macros.txt)
- **SocoCli:UseLocalCache** - Use cached speaker list (default: false)

## Troubleshooting

### Port Already in Use
If port 8080 or 8000 is already in use, you can find and kill the process:

```bash
# Find the process
lsof -i :8080

# Kill it
kill <PID>
```

### Speakers Not Found
1. Ensure your Sonos speakers are powered on
2. Check that your computer is on the same network as the speakers
3. Try manually discovering speakers: `sonos-discover`

### Permission Errors with pipx
If you encounter permission errors, try:

```bash
pipx install soco-cli --force
```

## Development

### Project Structure
```
/workspaces/SonosSoundHub/
├── api/                      # ASP.NET Core backend
│   ├── Controllers/          # API endpoints
│   ├── Models/              # Data models
│   ├── Services/            # Business logic
│   ├── wwwroot/             # Frontend files
│   │   ├── css/            # Stylesheets
│   │   ├── js/             # JavaScript modules
│   │   └── index.html      # Main UI
│   └── data/               # SQLite DB and macros
├── .devcontainer/           # Dev container config
└── README.md
```

### Frontend Architecture
- **Vanilla JavaScript** - No frameworks
- **Modular Design** - Separate files for API, UI, speakers, macros
- **Sonos-Inspired Theme** - Clean, modern aesthetic

### Backend Architecture
- **ASP.NET Core Web API** - RESTful endpoints
- **Service Layer** - Manages soco-cli process and commands
- **SQLite Database** - Local data storage
- **Static File Serving** - Serves frontend from wwwroot

## Next Steps

1. **Create Macros** - Use the Macros tab to create automated sequences
2. **Explore Speakers** - View and control all discovered speakers
3. **Customize UI** - Modify CSS in `wwwroot/css/`
4. **Extend Backend** - Add new endpoints in `Controllers/`
