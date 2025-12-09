using Microsoft.AspNetCore.Mvc;
using SonosSoundHub.Models;
using SonosSoundHub.Services;

namespace SonosSoundHub.Controllers;

/// <summary>
/// Controller for Sonos operations
/// </summary>
[ApiController]
[Route("api/[controller]")]
public class SonosController : ControllerBase
{
    private readonly ILogger<SonosController> _logger;
    private readonly SocoCliService _socoCliService;
    private readonly SonosCommandService _commandService;

    public SonosController(
        ILogger<SonosController> logger,
        SocoCliService socoCliService,
        SonosCommandService commandService)
    {
        _logger = logger;
        _socoCliService = socoCliService;
        _commandService = commandService;
    }

    /// <summary>
    /// Gets the status of the soco-cli server
    /// </summary>
    [HttpGet("status")]
    public ActionResult<SocoServerStatus> GetStatus()
    {
        return Ok(_socoCliService.GetStatus());
    }

    /// <summary>
    /// Starts the soco-cli HTTP API server
    /// </summary>
    [HttpPost("start")]
    public async Task<IActionResult> StartServer()
    {
        var result = await _socoCliService.StartServerAsync();
        if (result)
        {
            return Ok(new { message = "Server started successfully" });
        }
        return StatusCode(500, new { message = "Failed to start server" });
    }

    /// <summary>
    /// Stops the soco-cli HTTP API server
    /// </summary>
    [HttpPost("stop")]
    public IActionResult StopServer()
    {
        var result = _socoCliService.StopServer();
        if (result)
        {
            return Ok(new { message = "Server stopped successfully" });
        }
        return StatusCode(500, new { message = "Failed to stop server" });
    }

    /// <summary>
    /// Gets all discovered speakers
    /// </summary>
    [HttpGet("speakers")]
    public async Task<ActionResult<List<string>>> GetSpeakers()
    {
        var speakers = await _commandService.GetSpeakersAsync();
        return Ok(speakers);
    }

    /// <summary>
    /// Triggers speaker rediscovery
    /// </summary>
    [HttpPost("rediscover")]
    public async Task<ActionResult<List<string>>> RediscoverSpeakers()
    {
        var speakers = await _commandService.RediscoverSpeakersAsync();
        return Ok(speakers);
    }

    /// <summary>
    /// Gets detailed information about a speaker
    /// </summary>
    [HttpGet("speakers/{speakerName}")]
    public async Task<ActionResult<Speaker>> GetSpeakerInfo(string speakerName)
    {
        var speaker = await _commandService.GetSpeakerInfoAsync(speakerName);
        return Ok(speaker);
    }

    /// <summary>
    /// Executes a command on a speaker
    /// </summary>
    [HttpPost("command")]
    public async Task<ActionResult<SocoCliResponse>> ExecuteCommand([FromBody] SonosCommandRequest request)
    {
        var result = await _commandService.ExecuteCommandAsync(
            request.Speaker,
            request.Action,
            request.Args.ToArray()
        );
        return Ok(result);
    }

    /// <summary>
    /// Plays or pauses playback
    /// </summary>
    [HttpPost("speakers/{speakerName}/playpause")]
    public async Task<ActionResult<SocoCliResponse>> PlayPause(string speakerName)
    {
        var result = await _commandService.ExecuteCommandAsync(speakerName, "pauseplay");
        return Ok(result);
    }

    /// <summary>
    /// Sets the volume
    /// </summary>
    [HttpPost("speakers/{speakerName}/volume/{volume}")]
    public async Task<ActionResult<SocoCliResponse>> SetVolume(string speakerName, int volume)
    {
        if (volume < 0 || volume > 100)
        {
            return BadRequest(new { message = "Volume must be between 0 and 100" });
        }

        var result = await _commandService.ExecuteCommandAsync(speakerName, "volume", volume.ToString());
        return Ok(result);
    }

    /// <summary>
    /// Gets the current volume
    /// </summary>
    [HttpGet("speakers/{speakerName}/volume")]
    public async Task<ActionResult<int>> GetVolume(string speakerName)
    {
        var result = await _commandService.ExecuteCommandAsync(speakerName, "volume");
        if (result.ExitCode == 0 && int.TryParse(result.Result, out var volume))
        {
            return Ok(volume);
        }
        return StatusCode(500, new { message = "Failed to get volume" });
    }

    /// <summary>
    /// Toggles mute
    /// </summary>
    [HttpPost("speakers/{speakerName}/mute")]
    public async Task<ActionResult<SocoCliResponse>> ToggleMute(string speakerName)
    {
        // Get current mute state
        var currentState = await _commandService.ExecuteCommandAsync(speakerName, "mute");
        var newState = currentState.Result.ToLower() == "on" ? "off" : "on";
        
        var result = await _commandService.ExecuteCommandAsync(speakerName, "mute", newState);
        return Ok(result);
    }

    /// <summary>
    /// Gets the current track info
    /// </summary>
    [HttpGet("speakers/{speakerName}/track")]
    public async Task<ActionResult<string>> GetCurrentTrack(string speakerName)
    {
        var result = await _commandService.ExecuteCommandAsync(speakerName, "track");
        return Ok(new { track = result.Result });
    }

    /// <summary>
    /// Skips to the next track
    /// </summary>
    [HttpPost("speakers/{speakerName}/next")]
    public async Task<ActionResult<SocoCliResponse>> Next(string speakerName)
    {
        var result = await _commandService.ExecuteCommandAsync(speakerName, "next");
        return Ok(result);
    }

    /// <summary>
    /// Goes to the previous track
    /// </summary>
    [HttpPost("speakers/{speakerName}/previous")]
    public async Task<ActionResult<SocoCliResponse>> Previous(string speakerName)
    {
        var result = await _commandService.ExecuteCommandAsync(speakerName, "previous");
        return Ok(result);
    }
}
