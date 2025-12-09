# Copilot Instructions

## Project Overview
- **Frontend**: Vanilla JavaScript, HTML, CSS
- **Backend**: .NET C# API
- **Database**: Azure Table Storage and Blob Storage (no SQL)
- **Caching**: Managed Redis on Azure (with core classes for implementation)
- **Hosting**: Azure Static Web Apps
- **Architecture**: No view framework (React, Vue, etc.)

## Code Style Preferences

### General Philosophy
- **Fail fast**: Prefer things to fail when they don't work as intended
- **Simple fallbacks only**: Avoid long chains of fallbacks
- **Modern JavaScript**: Use modern ES6+ features (const/let, arrow functions, async/await)
- **Minimal comments**: Only comment complex logic

### Frontend (JavaScript)
- Use vanilla JavaScript only - no frameworks
- Fetch API for HTTP requests
- Always use relative URLs for API calls (e.g., `/api/users` not `https://domain.com/api/users`)
- Implement both client-side and server-side validation

### Backend (C#)
- Use async/await patterns
- Implement validation on all API endpoints
- Standard .NET C# API patterns
- Utilize Redis caching where appropriate
- Use Azure Table Storage for structured data
- Use Azure Blob Storage for files/documents
- **IMPORTANT**: Always use the `STORAGE` environment variable for Azure Storage connection strings (Table Storage and Blob Storage)
  - Local development: Uses Azurite (configured in `local.settings.json`)
  - Production: Uses Azure Storage Account (configured as Static Web App environment variable)
- **IMPORTANT**: Always configure JSON serialization to use camelCase for property names (JavaScript expects camelCase, not PascalCase)

### Error Handling
- Follow standard best practices
- Let errors fail fast rather than creating complex fallback chains
- Simple, straightforward error messages

## Documentation Requirements
- **JSDoc for JavaScript**: Document all functions with JSDoc comments
- **XML Documentation for C#**: Use XML documentation comments for all public methods
- **README files**: Include when needed for complex features or modules
- Focus on documenting the "why" not the "what" (code should be self-explanatory)

## Azure Static Web Apps Specifics
- API calls are proxied - always use relative URLs
- Backend API is automatically deployed and linked

## File Organization
- No specific naming conventions required
- Keep structure simple and logical

## Performance Considerations
- Utilize Redis caching through existing core classes
- Be mindful of bundle sizes in vanilla JS
- Follow Azure Static Web Apps best practices
- Consider Table Storage query patterns for performance

## Key Reminders
1. This is vanilla JavaScript - no React, Vue, or other frameworks
2. Always use relative URLs for API calls due to Azure Static Web Apps proxy
3. Fail fast - don't over-engineer error handling
4. Both frontend and backend validation is required
5. Keep comments minimal (but use proper JSDoc/XML documentation)
6. Use Table Storage and Blob Storage - no SQL databases
7. Implementing NEW backend APIs in C# is a big deal, please confirm you should do it, and clearly describe why it's needed
8. You should not use the AzureWebJobsStorage environment variable. Create a new one as this is reserved by Static Web Apps
9. Always use the `STORAGE` environment variable for all Azure Storage operations (Table Storage and Blob Storage)
10. Never commit secrets, connection strings, or the `tools/.azure-config` file to git
11. All API endpoints should be authenticated by default unless explicitly made public
12. Use camelCase for JSON properties sent to the frontend (JavaScript convention)
 