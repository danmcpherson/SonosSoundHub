using System.Text.Json;
using SonosSoundHub.Models;

namespace SonosSoundHub.Services;

/// <summary>
/// Service to execute commands via the soco-cli HTTP API
/// </summary>
public class SonosCommandService
{
    private readonly HttpClient _httpClient;
    private readonly SocoCliService _socoCliService;
    private readonly ILogger<SonosCommandService> _logger;

    public SonosCommandService(
        HttpClient httpClient,
        SocoCliService socoCliService,
        ILogger<SonosCommandService> logger)
    {
        _httpClient = httpClient;
        _socoCliService = socoCliService;
        _logger = logger;
    }

    /// <summary>
    /// Gets the list of speakers
    /// </summary>
    public async Task<List<string>> GetSpeakersAsync()
    {
        await _socoCliService.EnsureServerRunningAsync();

        try
        {
            var response = await _httpClient.GetAsync($"{_socoCliService.ServerUrl}/speakers");
            response.EnsureSuccessStatusCode();

            var content = await response.Content.ReadAsStringAsync();
            var result = JsonSerializer.Deserialize<JsonElement>(content);
            
            if (result.TryGetProperty("speakers", out var speakers))
            {
                return speakers.EnumerateArray()
                    .Select(s => s.GetString() ?? string.Empty)
                    .Where(s => !string.IsNullOrEmpty(s))
                    .ToList();
            }

            return new List<string>();
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Failed to get speakers");
            return new List<string>();
        }
    }

    /// <summary>
    /// Triggers speaker rediscovery
    /// </summary>
    public async Task<List<string>> RediscoverSpeakersAsync()
    {
        await _socoCliService.EnsureServerRunningAsync();

        try
        {
            var response = await _httpClient.GetAsync($"{_socoCliService.ServerUrl}/rediscover");
            response.EnsureSuccessStatusCode();

            var content = await response.Content.ReadAsStringAsync();
            var result = JsonSerializer.Deserialize<JsonElement>(content);
            
            if (result.TryGetProperty("speakers_discovered", out var speakers))
            {
                return speakers.EnumerateArray()
                    .Select(s => s.GetString() ?? string.Empty)
                    .Where(s => !string.IsNullOrEmpty(s))
                    .ToList();
            }

            return new List<string>();
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Failed to rediscover speakers");
            return new List<string>();
        }
    }

    /// <summary>
    /// Executes a command on a speaker
    /// </summary>
    public async Task<SocoCliResponse> ExecuteCommandAsync(string speaker, string action, params string[] args)
    {
        await _socoCliService.EnsureServerRunningAsync();

        try
        {
            var url = $"{_socoCliService.ServerUrl}/{Uri.EscapeDataString(speaker)}/{Uri.EscapeDataString(action)}";
            
            if (args.Length > 0)
            {
                var encodedArgs = args.Select(Uri.EscapeDataString);
                url += "/" + string.Join("/", encodedArgs);
            }

            _logger.LogInformation("Executing command: {Url}", url);

            var response = await _httpClient.GetAsync(url);
            response.EnsureSuccessStatusCode();

            var content = await response.Content.ReadAsStringAsync();
            var result = JsonSerializer.Deserialize<SocoCliResponse>(content, new JsonSerializerOptions
            {
                PropertyNameCaseInsensitive = true
            });

            return result ?? new SocoCliResponse { ErrorMsg = "Failed to parse response" };
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Failed to execute command: {Speaker} {Action}", speaker, action);
            return new SocoCliResponse
            {
                Speaker = speaker,
                Action = action,
                Args = args,
                ExitCode = -1,
                ErrorMsg = ex.Message
            };
        }
    }

    /// <summary>
    /// Gets detailed information about a speaker
    /// </summary>
    public async Task<Speaker> GetSpeakerInfoAsync(string speakerName)
    {
        var speaker = new Speaker { Name = speakerName };

        try
        {
            // Get volume
            var volumeResponse = await ExecuteCommandAsync(speakerName, "volume");
            if (volumeResponse.ExitCode == 0 && int.TryParse(volumeResponse.Result, out var volume))
            {
                speaker.Volume = volume;
            }

            // Get mute status
            var muteResponse = await ExecuteCommandAsync(speakerName, "mute");
            if (muteResponse.ExitCode == 0)
            {
                speaker.IsMuted = muteResponse.Result.ToLower() == "on";
            }

            // Get playback state
            var stateResponse = await ExecuteCommandAsync(speakerName, "playback");
            if (stateResponse.ExitCode == 0)
            {
                speaker.PlaybackState = stateResponse.Result;
            }

            // Get current track
            var trackResponse = await ExecuteCommandAsync(speakerName, "track");
            if (trackResponse.ExitCode == 0)
            {
                speaker.CurrentTrack = trackResponse.Result;
            }
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Failed to get speaker info for {Speaker}", speakerName);
        }

        return speaker;
    }
}
