using Microsoft.AspNetCore.Mvc;
using SonosSoundHub.Models;
using SonosSoundHub.Services;

namespace SonosSoundHub.Controllers;

/// <summary>
/// Controller for macro management
/// </summary>
[ApiController]
[Route("api/[controller]")]
public class MacroController : ControllerBase
{
    private readonly ILogger<MacroController> _logger;
    private readonly MacroService _macroService;

    public MacroController(ILogger<MacroController> logger, MacroService macroService)
    {
        _logger = logger;
        _macroService = macroService;
    }

    /// <summary>
    /// Gets all macros
    /// </summary>
    [HttpGet]
    public async Task<ActionResult<List<Macro>>> GetAllMacros()
    {
        var macros = await _macroService.GetAllMacrosAsync();
        return Ok(macros);
    }

    /// <summary>
    /// Gets macros file information
    /// </summary>
    [HttpGet("info")]
    public IActionResult GetMacrosInfo()
    {
        var info = _macroService.GetMacrosFileInfo();
        return Ok(info);
    }

    /// <summary>
    /// Gets a specific macro by name
    /// </summary>
    [HttpGet("{name}")]
    public async Task<ActionResult<Macro>> GetMacro(string name)
    {
        var macro = await _macroService.GetMacroAsync(name);
        if (macro == null)
        {
            return NotFound(new { message = $"Macro '{name}' not found" });
        }
        return Ok(macro);
    }

    /// <summary>
    /// Creates or updates a macro
    /// </summary>
    [HttpPost]
    public async Task<ActionResult<Macro>> SaveMacro([FromBody] Macro macro)
    {
        if (string.IsNullOrWhiteSpace(macro.Name))
        {
            return BadRequest(new { message = "Macro name is required" });
        }

        if (string.IsNullOrWhiteSpace(macro.Definition))
        {
            return BadRequest(new { message = "Macro definition is required" });
        }

        var result = await _macroService.SaveMacroAsync(macro);
        if (result)
        {
            return Ok(macro);
        }
        return StatusCode(500, new { message = "Failed to save macro" });
    }

    /// <summary>
    /// Deletes a macro
    /// </summary>
    [HttpDelete("{name}")]
    public async Task<IActionResult> DeleteMacro(string name)
    {
        var result = await _macroService.DeleteMacroAsync(name);
        if (result)
        {
            return Ok(new { message = $"Macro '{name}' deleted successfully" });
        }
        return NotFound(new { message = $"Macro '{name}' not found" });
    }

    /// <summary>
    /// Executes a macro
    /// </summary>
    [HttpPost("execute")]
    public async Task<IActionResult> ExecuteMacro([FromBody] MacroExecuteRequest request)
    {
        if (string.IsNullOrWhiteSpace(request.MacroName))
        {
            return BadRequest(new { message = "Macro name is required" });
        }

        try
        {
            var result = await _macroService.ExecuteMacroAsync(request.MacroName, request.Arguments);
            return Ok(result);
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Failed to execute macro: {Name}", request.MacroName);
            return StatusCode(500, new { message = $"Failed to execute macro: {ex.Message}" });
        }
    }

    /// <summary>
    /// Reloads all macros in the soco-cli server
    /// </summary>
    [HttpPost("reload")]
    public async Task<IActionResult> ReloadMacros()
    {
        var result = await _macroService.ReloadMacrosAsync();
        if (result)
        {
            return Ok(new { message = "Macros reloaded successfully" });
        }
        return StatusCode(500, new { message = "Failed to reload macros" });
    }

    /// <summary>
    /// Exports the macros file for download
    /// </summary>
    [HttpGet("export")]
    public async Task<IActionResult> ExportMacros()
    {
        try
        {
            var content = await _macroService.GetMacrosFileContentAsync();
            var bytes = System.Text.Encoding.UTF8.GetBytes(content);
            return File(bytes, "text/plain", "macros.txt");
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Failed to export macros");
            return StatusCode(500, new { message = "Failed to export macros" });
        }
    }

    /// <summary>
    /// Imports macros from an uploaded file
    /// </summary>
    [HttpPost("import")]
    public async Task<IActionResult> ImportMacros(IFormFile file, [FromQuery] bool merge = false)
    {
        if (file == null || file.Length == 0)
        {
            return BadRequest(new { message = "No file uploaded" });
        }

        try
        {
            using var reader = new StreamReader(file.OpenReadStream());
            var content = await reader.ReadToEndAsync();
            
            var result = await _macroService.ImportMacrosAsync(content, merge);
            if (result.Success)
            {
                return Ok(new { message = result.Message, imported = result.ImportedCount });
            }
            return BadRequest(new { message = result.Message });
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Failed to import macros");
            return StatusCode(500, new { message = $"Failed to import macros: {ex.Message}" });
        }
    }
}
