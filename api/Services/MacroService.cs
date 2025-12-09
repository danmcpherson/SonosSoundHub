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

        var dataDir = _configuration.GetValue<string>("DataDirectory", "data");
        _macrosFilePath = Path.Combine(dataDir, "macros.txt");
        _metadataFilePath = Path.Combine(dataDir, "macros-metadata.json");

        EnsureMacrosFileExists();
    }

    /// <summary>
    /// Ensures the macros file exists
    /// </summary>
    private void EnsureMacrosFileExists()
    {
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
}
