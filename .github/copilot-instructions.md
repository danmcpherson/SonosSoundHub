# Copilot Instructions

## Project Overview
- **Platform**: Raspberry Pi (ARM-compatible)
- **Frontend**: Vanilla JavaScript, HTML, CSS
- **Backend**: ASP.NET Core Web API (.NET 8)
- **Database**: SQLite (file-based, stored locally)
- **Caching**: In-memory caching (IMemoryCache)
- **Hosting**: Self-hosted on Raspberry Pi using Kestrel
- **Architecture**: No view framework (React, Vue, etc.), all runs locally

## Sonos Control Source
- **SoCo CLI**: Always consider wrapping or invoking functionality from the official SoCo CLI tool (`https://github.com/avantrec/soco-cli`), especially commands that translate well to a web interface (queue control, favorites, grouping, playback, and diagnostics). Prefer reusing those commands via the backend rather than re-implementing Sonos control logic from scratch.

## Code Style Preferences

### General Philosophy
- **Fail fast**: Prefer things to fail when they don't work as intended
- **Simple fallbacks only**: Avoid long chains of fallbacks
- **Modern JavaScript**: Use modern ES6+ features (const/let, arrow functions, async/await)
- **Minimal comments**: Only comment complex logic
### Frontend (JavaScript)
- Use vanilla JavaScript only - no frameworks
- Fetch API for HTTP requests
- Use relative URLs for API calls when served by same host, or localhost URLs for development
- Implement both client-side and server-side validation
- Keep frontend lightweight for optimal performance on Raspberry Pisers` not `https://domain.com/api/users`)
- Implement both client-side and server-side validation
### Backend (C#)
- Use async/await patterns
- Implement validation on all API endpoints
- Standard ASP.NET Core Web API patterns
- Utilize in-memory caching (IMemoryCache) where appropriate
- Use SQLite for structured data storage (connection string in `appsettings.json`)
- Store files in local filesystem (configured data directory)
- **IMPORTANT**: SQLite database file path should be configurable via `appsettings.json`
- **IMPORTANT**: All file storage should use relative paths from a configurable base directory
- **IMPORTANT**: Always configure JSON serialization to use camelCase for property names (JavaScript expects camelCase, not PascalCase)
- **IMPORTANT**: Ensure all code is ARM-compatible (avoid x86/x64-specific dependencies)
- **IMPORTANT**: Always configure JSON serialization to use camelCase for property names (JavaScript expects camelCase, not PascalCase)

### Error Handling
- Follow standard best practices
- Let errors fail fast rather than creating complex fallback chains
- Simple, straightforward error messages

## Documentation Requirements
- **JSDoc for JavaScript**: Document all functions with JSDoc comments
- **XML Documentation for C#**: Use XML documentation comments for all public methods
- **README files**: Include when needed for complex features or modules
## Raspberry Pi Specifics
- Application runs entirely on the local device
- Frontend served via ASP.NET Core static file middleware
- Backend API runs on same Kestrel server (different routes)
- Default port: 5000 (HTTP) or 5001 (HTTPS)
- Use systemd service for auto-start on boot (optional)

## File Organization
- No specific naming conventions required
- Keep structure simple and logical
- SQLite database and uploaded files stored in `/data` directory (configurable)

## Performance Considerations
- Raspberry Pi has limited resources - optimize for ARM architecture
## Key Reminders
1. This is vanilla JavaScript - no React, Vue, or other frameworks
2. Everything runs locally on Raspberry Pi - no cloud dependencies
3. Fail fast - don't over-engineer error handling
4. Both frontend and backend validation is required
5. Keep comments minimal (but use proper JSDoc/XML documentation)
6. Use SQLite for data storage - it's file-based and perfect for Raspberry Pi
7. Implementing NEW backend APIs in C# is a big deal, please confirm you should do it, and clearly describe why it's needed
8. Use relative paths for file storage, configurable via `appsettings.json`
9. Never commit secrets, database files, or the `data/` directory to git
10. All API endpoints should be authenticated by default unless explicitly made public
11. Use camelCase for JSON properties sent to the frontend (JavaScript convention)
12. Ensure ARM compatibility - avoid platform-specific dependencies
13. Optimize for limited resources (CPU, RAM) on Raspberry Pi
5. Keep comments minimal (but use proper JSDoc/XML documentation)
6. Use Table Storage and Blob Storage - no SQL databases
7. Implementing NEW backend APIs in C# is a big deal, please confirm you should do it, and clearly describe why it's needed
8. You should not use the AzureWebJobsStorage environment variable. Create a new one as this is reserved by Static Web Apps
9. Always use the `STORAGE` environment variable for all Azure Storage operations (Table Storage and Blob Storage)
10. Never commit secrets, connection strings, or the `tools/.azure-config` file to git
11. All API endpoints should be authenticated by default unless explicitly made public
12. Use camelCase for JSON properties sent to the frontend (JavaScript convention)
 