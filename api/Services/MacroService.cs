using System.Text;
using System.Text.Json;
using System.Text.RegularExpressions;
using SonosSoundHub.Models;

namespace SonosSoundHub.Services;

/// <summary>
/// Service to manage Sonos macros
/// </summary>
public class MacroService
{
    private readonly ILogger<MacroService> _logger;
    private readonly IConfiguration _configuration;
    private readonly SocoCliService _socoCliService;
    private readonly HttpClient _httpClient;
    private readonly string _macrosFilePath;
    private readonly string _metadataFilePath;

    public MacroService(
        ILogger<MacroService> logger,
        IConfiguration configuration,
        SocoCliService socoCliService,
        HttpClient httpClient)
    {
        _logger = logger;
        _configuration = configuration;
        _socoCliService = socoCliService;
        _httpClient = httpClient;

        var dataDir = _configuration.GetValue<string>("DataDirectory") ?? "data";
        // Convert to absolute path to ensure consistency with soco-cli server
        _macrosFilePath = Path.GetFullPath(Path.Combine(dataDir, "macros.txt"));
        _metadataFilePath = Path.GetFullPath(Path.Combine(dataDir, "macros-metadata.json"));

        EnsureMacrosFileExists();
    }

    /// <summary>
    /// Ensures the macros file exists
    /// </summary>
    private void EnsureMacrosFileExists()
    {
        // Ensure directory exists
        var directory = Path.GetDirectoryName(_macrosFilePath);
        if (!string.IsNullOrEmpty(directory) && !Directory.Exists(directory))
        {
            Directory.CreateDirectory(directory);
            _logger.LogInformation("Created data directory: {Directory}", directory);
        }

        if (!File.Exists(_macrosFilePath))
        {
            var defaultContent = @"# SonosSoundHub Macros
# Format: macro_name = speaker action args : speaker action args
# Example: morning = Kitchen volume 40 : Kitchen play_favourite ""Radio 4""

";
            File.WriteAllText(_macrosFilePath, defaultContent);
            _logger.LogInformation("Created default macros file at {Path}", _macrosFilePath);
        }
    }

    /// <summary>
    /// Gets information about the macros file
    /// </summary>
    public object GetMacrosFileInfo()
    {
        return new
        {
            FilePath = _macrosFilePath,
            FileExists = File.Exists(_macrosFilePath)
        };
    }

    /// <summary>
    /// Gets all macros from the file
    /// </summary>
    public async Task<List<Macro>> GetAllMacrosAsync()
    {
        var macros = new List<Macro>();
        var metadata = await LoadMetadataAsync();

        try
        {
            var lines = await File.ReadAllLinesAsync(_macrosFilePath);
            
            foreach (var line in lines)
            {
                if (string.IsNullOrWhiteSpace(line) || line.TrimStart().StartsWith("#"))
                {
                    continue;
                }

                var parts = line.Split('=', 2);
                if (parts.Length == 2)
                {
                    var name = parts[0].Trim();
                    var definition = parts[1].Trim();

                    var macro = new Macro
                    {
                        Name = name,
                        Definition = definition
                    };

                    // Load metadata if available
                    if (metadata.TryGetValue(name, out var meta))
                    {
                        macro.Description = meta.Description;
                        macro.Category = meta.Category;
                        macro.IsFavorite = meta.IsFavorite;
                        macro.Parameters = meta.Parameters;
                    }
                    else
                    {
                        // Auto-detect parameters
                        macro.Parameters = DetectParameters(definition);
                    }

                    macros.Add(macro);
                }
            }
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Failed to read macros file");
        }

        return macros;
    }

    /// <summary>
    /// Gets a specific macro by name
    /// </summary>
    public async Task<Macro?> GetMacroAsync(string name)
    {
        var macros = await GetAllMacrosAsync();
        return macros.FirstOrDefault(m => m.Name.Equals(name, StringComparison.OrdinalIgnoreCase));
    }

    /// <summary>
    /// Saves or updates a macro
    /// </summary>
    public async Task<bool> SaveMacroAsync(Macro macro)
    {
        try
        {
            var macros = await GetAllMacrosAsync();
            var existing = macros.FirstOrDefault(m => m.Name.Equals(macro.Name, StringComparison.OrdinalIgnoreCase));

            if (existing != null)
            {
                macros.Remove(existing);
            }

            macros.Add(macro);

            // Write to file
            var sb = new StringBuilder();
            sb.AppendLine("# SonosSoundHub Macros");
            sb.AppendLine("# Format: macro_name = speaker action args : speaker action args");
            sb.AppendLine();

            foreach (var m in macros.OrderBy(m => m.Name))
            {
                if (!string.IsNullOrEmpty(m.Description))
                {
                    sb.AppendLine($"# {m.Description}");
                }
                sb.AppendLine($"{m.Name} = {m.Definition}");
                sb.AppendLine();
            }

            await File.WriteAllTextAsync(_macrosFilePath, sb.ToString());

            // Save metadata
            await SaveMetadataAsync(macros);

            // Reload macros in soco-cli server
            await ReloadMacrosAsync();

            _logger.LogInformation("Saved macro: {Name}", macro.Name);
            return true;
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Failed to save macro: {Name}", macro.Name);
            return false;
        }
    }

    /// <summary>
    /// Deletes a macro
    /// </summary>
    public async Task<bool> DeleteMacroAsync(string name)
    {
        try
        {
            var macros = await GetAllMacrosAsync();
            var toRemove = macros.FirstOrDefault(m => m.Name.Equals(name, StringComparison.OrdinalIgnoreCase));

            if (toRemove == null)
            {
                return false;
            }

            macros.Remove(toRemove);

            // Write to file
            var sb = new StringBuilder();
            sb.AppendLine("# SonosSoundHub Macros");
            sb.AppendLine();

            foreach (var m in macros.OrderBy(m => m.Name))
            {
                if (!string.IsNullOrEmpty(m.Description))
                {
                    sb.AppendLine($"# {m.Description}");
                }
                sb.AppendLine($"{m.Name} = {m.Definition}");
                sb.AppendLine();
            }

            await File.WriteAllTextAsync(_macrosFilePath, sb.ToString());

            // Save metadata
            await SaveMetadataAsync(macros);

            // Reload macros in soco-cli server
            await ReloadMacrosAsync();

            _logger.LogInformation("Deleted macro: {Name}", name);
            return true;
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Failed to delete macro: {Name}", name);
            return false;
        }
    }

    /// <summary>
    /// Executes a macro
    /// </summary>
    public async Task<JsonElement> ExecuteMacroAsync(string macroName, List<string> arguments)
    {
        await _socoCliService.EnsureServerRunningAsync();

        try
        {
            var url = $"{_socoCliService.ServerUrl}/macro/{Uri.EscapeDataString(macroName)}";
            
            if (arguments.Count > 0)
            {
                var encodedArgs = arguments.Select(Uri.EscapeDataString);
                url += "/" + string.Join("/", encodedArgs);
            }

            _logger.LogInformation("Executing macro: {Url}", url);

            var response = await _httpClient.GetAsync(url);
            response.EnsureSuccessStatusCode();

            var content = await response.Content.ReadAsStringAsync();
            return JsonSerializer.Deserialize<JsonElement>(content);
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Failed to execute macro: {Name}", macroName);
            throw;
        }
    }

    /// <summary>
    /// Reloads macros in the soco-cli server
    /// </summary>
    public async Task<bool> ReloadMacrosAsync()
    {
        await _socoCliService.EnsureServerRunningAsync();

        try
        {
            var response = await _httpClient.GetAsync($"{_socoCliService.ServerUrl}/macros/reload");
            response.EnsureSuccessStatusCode();
            _logger.LogInformation("Reloaded macros in soco-cli server");
            return true;
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Failed to reload macros");
            return false;
        }
    }

    /// <summary>
    /// Detects parameters in a macro definition
    /// </summary>
    private List<MacroParameter> DetectParameters(string definition)
    {
        var parameters = new List<MacroParameter>();
        var regex = new Regex(@"%(\d+)");
        var matches = regex.Matches(definition);

        foreach (Match match in matches)
        {
            var position = int.Parse(match.Groups[1].Value);
            if (!parameters.Any(p => p.Position == position))
            {
                parameters.Add(new MacroParameter
                {
                    Position = position,
                    Name = $"Parameter {position}",
                    Type = "string"
                });
            }
        }

        return parameters.OrderBy(p => p.Position).ToList();
    }

    /// <summary>
    /// Loads metadata from JSON file
    /// </summary>
    private async Task<Dictionary<string, Macro>> LoadMetadataAsync()
    {
        if (!File.Exists(_metadataFilePath))
        {
            return new Dictionary<string, Macro>();
        }

        try
        {
            var json = await File.ReadAllTextAsync(_metadataFilePath);
            var macros = JsonSerializer.Deserialize<List<Macro>>(json) ?? new List<Macro>();
            return macros.ToDictionary(m => m.Name, StringComparer.OrdinalIgnoreCase);
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Failed to load macro metadata");
            return new Dictionary<string, Macro>();
        }
    }

    /// <summary>
    /// Saves metadata to JSON file
    /// </summary>
    private async Task SaveMetadataAsync(List<Macro> macros)
    {
        try
        {
            var json = JsonSerializer.Serialize(macros, new JsonSerializerOptions
            {
                WriteIndented = true,
                PropertyNamingPolicy = JsonNamingPolicy.CamelCase
            });
            await File.WriteAllTextAsync(_metadataFilePath, json);
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Failed to save macro metadata");
        }
    }

    /// <summary>
    /// Gets the raw macros file content for export
    /// </summary>
    public async Task<string> GetMacrosFileContentAsync()
    {
        if (!File.Exists(_macrosFilePath))
        {
            return string.Empty;
        }
        return await File.ReadAllTextAsync(_macrosFilePath);
    }

    /// <summary>
    /// Imports macros from file content
    /// </summary>
    public async Task<ImportResult> ImportMacrosAsync(string content, bool merge = false)
    {
        var result = new ImportResult();

        try
        {
            // Parse the imported content to validate it
            var importedMacros = ParseMacrosFile(content);
            
            if (importedMacros.Count == 0)
            {
                result.Message = "No valid macros found in the imported file";
                return result;
            }

            if (merge)
            {
                // Merge with existing macros
                var existingContent = await GetMacrosFileContentAsync();
                var existingMacros = ParseMacrosFile(existingContent);
                
                // Add new macros, skip existing ones
                var newMacros = new List<string>();
                foreach (var macro in importedMacros)
                {
                    if (!existingMacros.ContainsKey(macro.Key))
                    {
                        newMacros.Add($"{macro.Key} = {macro.Value}");
                        result.ImportedCount++;
                    }
                }

                if (newMacros.Count > 0)
                {
                    // Append to existing file
                    var appendContent = "\n# Imported macros\n" + string.Join("\n", newMacros) + "\n";
                    await File.AppendAllTextAsync(_macrosFilePath, appendContent);
                    result.Message = $"Merged {result.ImportedCount} new macros (skipped {importedMacros.Count - result.ImportedCount} existing)";
                }
                else
                {
                    result.Message = "All macros already exist, nothing to import";
                }
            }
            else
            {
                // Replace entire file
                await File.WriteAllTextAsync(_macrosFilePath, content);
                result.ImportedCount = importedMacros.Count;
                result.Message = $"Imported {result.ImportedCount} macros (replaced existing file)";
            }

            result.Success = true;
            
            // Reload macros in soco-cli
            await ReloadMacrosAsync();
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Failed to import macros");
            result.Message = $"Failed to import macros: {ex.Message}";
        }

        return result;
    }

    /// <summary>
    /// Parses macros file content into a dictionary
    /// </summary>
    private Dictionary<string, string> ParseMacrosFile(string content)
    {
        var macros = new Dictionary<string, string>(StringComparer.OrdinalIgnoreCase);
        var lines = content.Split('\n');

        foreach (var line in lines)
        {
            var trimmed = line.Trim();
            if (string.IsNullOrEmpty(trimmed) || trimmed.StartsWith('#'))
            {
                continue;
            }

            var equalsIndex = trimmed.IndexOf('=');
            if (equalsIndex > 0)
            {
                var name = trimmed.Substring(0, equalsIndex).Trim();
                var definition = trimmed.Substring(equalsIndex + 1).Trim();
                if (!string.IsNullOrEmpty(name) && !string.IsNullOrEmpty(definition))
                {
                    macros[name] = definition;
                }
            }
        }

        return macros;
    }
}

/// <summary>
/// Result of a macro import operation
/// </summary>
public class ImportResult
{
    public bool Success { get; set; }
    public string Message { get; set; } = string.Empty;
    public int ImportedCount { get; set; }
}
