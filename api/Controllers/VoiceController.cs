using Microsoft.AspNetCore.Mvc;
using System.Net.Http.Headers;
using System.Text.Json;

namespace SonosSoundHub.Controllers;

/// <summary>
/// Controller for OpenAI Realtime API session management
/// </summary>
[ApiController]
[Route("api/[controller]")]
public class VoiceController : ControllerBase
{
    private readonly ILogger<VoiceController> _logger;
    private readonly IConfiguration _configuration;
    private readonly HttpClient _httpClient;
    
    // Store API key in memory (for user-provided keys)
    private static string? _userProvidedApiKey;
    
    // Available voices
    private static readonly string[] AvailableVoices = { "verse", "alloy", "ash", "ballad", "coral", "echo", "sage", "shimmer" };

    public VoiceController(
        ILogger<VoiceController> logger,
        IConfiguration configuration,
        IHttpClientFactory httpClientFactory)
    {
        _logger = logger;
        _configuration = configuration;
        _httpClient = httpClientFactory.CreateClient();
    }
    
    /// <summary>
    /// Get the effective API key (user-provided or from config)
    /// </summary>
    private string? GetApiKey()
    {
        // User-provided key takes precedence
        if (!string.IsNullOrEmpty(_userProvidedApiKey))
            return _userProvidedApiKey;
        
        return _configuration["OpenAI:ApiKey"];
    }

    /// <summary>
    /// Gets an ephemeral session token for the OpenAI Realtime API.
    /// This keeps the API key secure on the server.
    /// </summary>
    [HttpPost("session")]
    public async Task<IActionResult> CreateSession([FromQuery] string? voice = "verse")
    {
        var apiKey = GetApiKey();
        
        if (string.IsNullOrEmpty(apiKey))
        {
            _logger.LogWarning("OpenAI API key not configured");
            return BadRequest(new { 
                error = "OpenAI API key not configured",
                message = "Add OpenAI:ApiKey to appsettings.json or enter your API key in the Voice settings"
            });
        }
        
        // Validate voice selection
        if (!AvailableVoices.Contains(voice?.ToLower() ?? "verse"))
        {
            voice = "verse";
        }

        try
        {
            var request = new HttpRequestMessage(HttpMethod.Post, "https://api.openai.com/v1/realtime/sessions");
            request.Headers.Authorization = new AuthenticationHeaderValue("Bearer", apiKey);
            request.Content = new StringContent(JsonSerializer.Serialize(new
            {
                model = "gpt-4o-realtime-preview-2024-12-17",
                voice = voice?.ToLower() ?? "verse",
                instructions = GetSystemInstructions(),
                tools = GetSonosTools(),
                tool_choice = "auto",
                input_audio_transcription = new { model = "whisper-1" },
                turn_detection = new
                {
                    type = "server_vad",
                    threshold = 0.5,
                    prefix_padding_ms = 300,
                    silence_duration_ms = 500
                }
            }), System.Text.Encoding.UTF8, "application/json");

            var response = await _httpClient.SendAsync(request);
            var content = await response.Content.ReadAsStringAsync();

            if (!response.IsSuccessStatusCode)
            {
                _logger.LogError("OpenAI session creation failed: {Status} {Content}", response.StatusCode, content);
                
                // If unauthorized, the API key might be invalid
                if (response.StatusCode == System.Net.HttpStatusCode.Unauthorized)
                {
                    return StatusCode(401, new { error = "Invalid API key", message = "The provided API key is not valid" });
                }
                
                return StatusCode((int)response.StatusCode, new { error = "Failed to create session", details = content });
            }

            var sessionData = JsonSerializer.Deserialize<JsonElement>(content);
            return Ok(sessionData);
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Failed to create OpenAI session");
            return StatusCode(500, new { error = "Failed to create session", message = ex.Message });
        }
    }

    /// <summary>
    /// Check if voice feature is configured
    /// </summary>
    [HttpGet("status")]
    public IActionResult GetStatus()
    {
        var apiKey = GetApiKey();
        return Ok(new
        {
            configured = !string.IsNullOrEmpty(apiKey),
            availableVoices = AvailableVoices,
            message = string.IsNullOrEmpty(apiKey) 
                ? "Enter your OpenAI API key to enable voice control"
                : "Voice control is configured and ready"
        });
    }
    
    /// <summary>
    /// Save user-provided API key
    /// </summary>
    [HttpPost("apikey")]
    public IActionResult SaveApiKey([FromBody] ApiKeyRequest request)
    {
        if (string.IsNullOrWhiteSpace(request?.ApiKey))
        {
            return BadRequest(new { error = "API key is required" });
        }
        
        // Basic validation - OpenAI keys start with "sk-"
        if (!request.ApiKey.StartsWith("sk-"))
        {
            return BadRequest(new { error = "Invalid API key format. OpenAI API keys start with 'sk-'" });
        }
        
        _userProvidedApiKey = request.ApiKey;
        _logger.LogInformation("User provided OpenAI API key saved (in memory only)");
        
        return Ok(new { 
            success = true, 
            message = "API key saved. Note: This key is stored in memory and will be lost when the server restarts." 
        });
    }
    
    /// <summary>
    /// Clear user-provided API key
    /// </summary>
    [HttpDelete("apikey")]
    public IActionResult ClearApiKey()
    {
        _userProvidedApiKey = null;
        _logger.LogInformation("User-provided API key cleared");
        return Ok(new { success = true, message = "API key cleared" });
    }

    private static string GetSystemInstructions()
    {
        return @"You are a helpful voice assistant for controlling a Sonos speaker system. You help users:

- Play, pause, and control music playback
- Adjust volume on speakers
- Group and ungroup speakers
- Play favorites, playlists, and radio stations
- Run automation macros
- Get information about what's playing

Be concise and friendly in your responses. When executing commands, confirm what you did briefly.

Speaker names in this system may include: Kitchen, Living Room, Bedroom, Office, Dining Room, etc.
Users may refer to speakers casually - match to the closest speaker name.

When users ask about macros, list them briefly. When they want to run one, use the run_macro function.

Always respond conversationally and confirm actions you take.";
    }

    private static object[] GetSonosTools()
    {
        return new object[]
        {
            // Speaker Discovery
            new
            {
                type = "function",
                name = "list_speakers",
                description = "Get a list of all discovered Sonos speakers on the network",
                parameters = new { type = "object", properties = new { }, required = Array.Empty<string>() }
            },
            new
            {
                type = "function",
                name = "get_speaker_info",
                description = "Get detailed information about a speaker including volume, playback state, current track, and battery level",
                parameters = new
                {
                    type = "object",
                    properties = new
                    {
                        speaker = new { type = "string", description = "Name of the Sonos speaker" }
                    },
                    required = new[] { "speaker" }
                }
            },

            // Playback Control
            new
            {
                type = "function",
                name = "play_pause",
                description = "Toggle play/pause on a Sonos speaker",
                parameters = new
                {
                    type = "object",
                    properties = new
                    {
                        speaker = new { type = "string", description = "Name of the Sonos speaker" }
                    },
                    required = new[] { "speaker" }
                }
            },
            new
            {
                type = "function",
                name = "next_track",
                description = "Skip to the next track on a Sonos speaker",
                parameters = new
                {
                    type = "object",
                    properties = new
                    {
                        speaker = new { type = "string", description = "Name of the Sonos speaker" }
                    },
                    required = new[] { "speaker" }
                }
            },
            new
            {
                type = "function",
                name = "previous_track",
                description = "Go back to the previous track on a Sonos speaker",
                parameters = new
                {
                    type = "object",
                    properties = new
                    {
                        speaker = new { type = "string", description = "Name of the Sonos speaker" }
                    },
                    required = new[] { "speaker" }
                }
            },
            new
            {
                type = "function",
                name = "get_current_track",
                description = "Get information about the currently playing track",
                parameters = new
                {
                    type = "object",
                    properties = new
                    {
                        speaker = new { type = "string", description = "Name of the Sonos speaker" }
                    },
                    required = new[] { "speaker" }
                }
            },

            // Volume Control
            new
            {
                type = "function",
                name = "get_volume",
                description = "Get the current volume level of a speaker (0-100)",
                parameters = new
                {
                    type = "object",
                    properties = new
                    {
                        speaker = new { type = "string", description = "Name of the Sonos speaker" }
                    },
                    required = new[] { "speaker" }
                }
            },
            new
            {
                type = "function",
                name = "set_volume",
                description = "Set the volume level of a speaker (0-100)",
                parameters = new
                {
                    type = "object",
                    properties = new
                    {
                        speaker = new { type = "string", description = "Name of the Sonos speaker" },
                        volume = new { type = "integer", description = "Volume level from 0 to 100" }
                    },
                    required = new[] { "speaker", "volume" }
                }
            },
            new
            {
                type = "function",
                name = "toggle_mute",
                description = "Toggle mute on/off for a speaker",
                parameters = new
                {
                    type = "object",
                    properties = new
                    {
                        speaker = new { type = "string", description = "Name of the Sonos speaker" }
                    },
                    required = new[] { "speaker" }
                }
            },

            // Grouping
            new
            {
                type = "function",
                name = "get_groups",
                description = "Get all current speaker groups",
                parameters = new { type = "object", properties = new { }, required = Array.Empty<string>() }
            },
            new
            {
                type = "function",
                name = "group_speakers",
                description = "Group a speaker with another speaker (the coordinator)",
                parameters = new
                {
                    type = "object",
                    properties = new
                    {
                        speaker = new { type = "string", description = "Name of the speaker to add to the group" },
                        coordinator = new { type = "string", description = "Name of the speaker that will be the group coordinator" }
                    },
                    required = new[] { "speaker", "coordinator" }
                }
            },
            new
            {
                type = "function",
                name = "ungroup_speaker",
                description = "Remove a speaker from its current group",
                parameters = new
                {
                    type = "object",
                    properties = new
                    {
                        speaker = new { type = "string", description = "Name of the Sonos speaker to ungroup" }
                    },
                    required = new[] { "speaker" }
                }
            },
            new
            {
                type = "function",
                name = "party_mode",
                description = "Group all speakers together (party mode)",
                parameters = new
                {
                    type = "object",
                    properties = new
                    {
                        speaker = new { type = "string", description = "Name of the speaker to be the coordinator" }
                    },
                    required = new[] { "speaker" }
                }
            },
            new
            {
                type = "function",
                name = "ungroup_all",
                description = "Ungroup all speakers - each speaker will play independently",
                parameters = new
                {
                    type = "object",
                    properties = new
                    {
                        speaker = new { type = "string", description = "Any speaker name" }
                    },
                    required = new[] { "speaker" }
                }
            },
            new
            {
                type = "function",
                name = "set_group_volume",
                description = "Set the volume for all speakers in a group",
                parameters = new
                {
                    type = "object",
                    properties = new
                    {
                        speaker = new { type = "string", description = "Name of any speaker in the group" },
                        volume = new { type = "integer", description = "Volume level from 0 to 100" }
                    },
                    required = new[] { "speaker", "volume" }
                }
            },

            // Playback Modes
            new
            {
                type = "function",
                name = "set_shuffle",
                description = "Enable or disable shuffle mode",
                parameters = new
                {
                    type = "object",
                    properties = new
                    {
                        speaker = new { type = "string", description = "Name of the Sonos speaker" },
                        enabled = new { type = "boolean", description = "True to enable shuffle, false to disable" }
                    },
                    required = new[] { "speaker", "enabled" }
                }
            },
            new
            {
                type = "function",
                name = "set_repeat",
                description = "Set the repeat mode",
                parameters = new
                {
                    type = "object",
                    properties = new
                    {
                        speaker = new { type = "string", description = "Name of the Sonos speaker" },
                        mode = new { type = "string", description = "Repeat mode: 'off', 'one', or 'all'" }
                    },
                    required = new[] { "speaker", "mode" }
                }
            },
            new
            {
                type = "function",
                name = "set_sleep_timer",
                description = "Set a sleep timer to stop playback after a duration",
                parameters = new
                {
                    type = "object",
                    properties = new
                    {
                        speaker = new { type = "string", description = "Name of the Sonos speaker" },
                        minutes = new { type = "integer", description = "Number of minutes until playback stops (0 to cancel)" }
                    },
                    required = new[] { "speaker", "minutes" }
                }
            },

            // Favorites & Playlists
            new
            {
                type = "function",
                name = "list_favorites",
                description = "Get all Sonos favorites",
                parameters = new { type = "object", properties = new { }, required = Array.Empty<string>() }
            },
            new
            {
                type = "function",
                name = "play_favorite",
                description = "Play a Sonos favorite by name",
                parameters = new
                {
                    type = "object",
                    properties = new
                    {
                        speaker = new { type = "string", description = "Name of the Sonos speaker" },
                        favorite_name = new { type = "string", description = "Name of the favorite to play" }
                    },
                    required = new[] { "speaker", "favorite_name" }
                }
            },
            new
            {
                type = "function",
                name = "list_playlists",
                description = "Get all Sonos playlists",
                parameters = new { type = "object", properties = new { }, required = Array.Empty<string>() }
            },
            new
            {
                type = "function",
                name = "list_radio_stations",
                description = "Get favorite radio stations",
                parameters = new { type = "object", properties = new { }, required = Array.Empty<string>() }
            },
            new
            {
                type = "function",
                name = "play_radio",
                description = "Play a radio station by name",
                parameters = new
                {
                    type = "object",
                    properties = new
                    {
                        speaker = new { type = "string", description = "Name of the Sonos speaker" },
                        station_name = new { type = "string", description = "Name of the radio station to play" }
                    },
                    required = new[] { "speaker", "station_name" }
                }
            },

            // Queue Management
            new
            {
                type = "function",
                name = "get_queue",
                description = "Get the current playback queue",
                parameters = new
                {
                    type = "object",
                    properties = new
                    {
                        speaker = new { type = "string", description = "Name of the Sonos speaker" }
                    },
                    required = new[] { "speaker" }
                }
            },
            new
            {
                type = "function",
                name = "clear_queue",
                description = "Clear all tracks from the queue",
                parameters = new
                {
                    type = "object",
                    properties = new
                    {
                        speaker = new { type = "string", description = "Name of the Sonos speaker" }
                    },
                    required = new[] { "speaker" }
                }
            },
            new
            {
                type = "function",
                name = "play_from_queue",
                description = "Play a specific track from the queue by its position number",
                parameters = new
                {
                    type = "object",
                    properties = new
                    {
                        speaker = new { type = "string", description = "Name of the Sonos speaker" },
                        track_number = new { type = "integer", description = "Position of the track in the queue (1-based)" }
                    },
                    required = new[] { "speaker", "track_number" }
                }
            },
            new
            {
                type = "function",
                name = "add_favorite_to_queue",
                description = "Add a favorite to the end of the queue",
                parameters = new
                {
                    type = "object",
                    properties = new
                    {
                        speaker = new { type = "string", description = "Name of the Sonos speaker" },
                        favorite_name = new { type = "string", description = "Name of the favorite to add" }
                    },
                    required = new[] { "speaker", "favorite_name" }
                }
            },
            new
            {
                type = "function",
                name = "add_playlist_to_queue",
                description = "Add a playlist to the end of the queue",
                parameters = new
                {
                    type = "object",
                    properties = new
                    {
                        speaker = new { type = "string", description = "Name of the Sonos speaker" },
                        playlist_name = new { type = "string", description = "Name of the playlist to add" }
                    },
                    required = new[] { "speaker", "playlist_name" }
                }
            },

            // Macros
            new
            {
                type = "function",
                name = "list_macros",
                description = "Get all available Sonos macros (automated sequences of commands)",
                parameters = new { type = "object", properties = new { }, required = Array.Empty<string>() }
            },
            new
            {
                type = "function",
                name = "get_macro",
                description = "Get details of a specific macro including its definition",
                parameters = new
                {
                    type = "object",
                    properties = new
                    {
                        name = new { type = "string", description = "Name of the macro" }
                    },
                    required = new[] { "name" }
                }
            },
            new
            {
                type = "function",
                name = "run_macro",
                description = "Execute a macro to run a predefined sequence of Sonos commands",
                parameters = new
                {
                    type = "object",
                    properties = new
                    {
                        name = new { type = "string", description = "Name of the macro to execute" },
                        arguments = new
                        {
                            type = "array",
                            items = new { type = "string" },
                            description = "Optional arguments to pass to the macro"
                        }
                    },
                    required = new[] { "name" }
                }
            }
        };
    }
}

/// <summary>
/// Request model for saving API key
/// </summary>
public class ApiKeyRequest
{
    public string? ApiKey { get; set; }
}
