using System.Diagnostics;
using System.Text.RegularExpressions;

namespace SonosSoundHub.Services;

/// <summary>
/// Service to manage the soco-cli HTTP API server process
/// </summary>
public class SocoCliService
{
    private readonly ILogger<SocoCliService> _logger;
    private readonly IConfiguration _configuration;
    private Process? _serverProcess;
    private DateTime? _startedAt;
    private readonly int _port;

    public SocoCliService(ILogger<SocoCliService> logger, IConfiguration configuration)
    {
        _logger = logger;
        _configuration = configuration;
        _port = _configuration.GetValue<int>("SocoCli:Port", 8000);
    }

    /// <summary>
    /// Gets the soco-cli server URL
    /// </summary>
    public string ServerUrl => $"http://localhost:{_port}";

    /// <summary>
    /// Checks if the soco-cli HTTP API server is running
    /// </summary>
    public bool IsRunning()
    {
        return _serverProcess != null && !_serverProcess.HasExited;
    }

    /// <summary>
    /// Gets the current server status
    /// </summary>
    public Models.SocoServerStatus GetStatus()
    {
        return new Models.SocoServerStatus
        {
            IsRunning = IsRunning(),
            ProcessId = _serverProcess?.Id,
            ServerUrl = IsRunning() ? ServerUrl : null,
            StartedAt = _startedAt
        };
    }

    /// <summary>
    /// Starts the soco-cli HTTP API server
    /// </summary>
    public async Task<bool> StartServerAsync()
    {
        if (IsRunning())
        {
            _logger.LogInformation("Soco-CLI server is already running");
            return true;
        }

        try
        {
            var macrosFile = _configuration.GetValue<string>("SocoCli:MacrosFile", "data/macros.txt");
            var useLocalCache = _configuration.GetValue<bool>("SocoCli:UseLocalCache", false);

            var arguments = $"--port {_port}";
            
            if (!string.IsNullOrEmpty(macrosFile))
            {
                arguments += $" --macros {macrosFile}";
            }

            if (useLocalCache)
            {
                arguments += " --use-local-speaker-list";
            }

            var startInfo = new ProcessStartInfo
            {
                FileName = "sonos-http-api-server",
                Arguments = arguments,
                UseShellExecute = false,
                RedirectStandardOutput = true,
                RedirectStandardError = true,
                CreateNoWindow = true
            };

            _serverProcess = new Process { StartInfo = startInfo };
            
            _serverProcess.OutputDataReceived += (sender, e) =>
            {
                if (!string.IsNullOrEmpty(e.Data))
                {
                    _logger.LogInformation("soco-cli: {Output}", e.Data);
                }
            };

            _serverProcess.ErrorDataReceived += (sender, e) =>
            {
                if (!string.IsNullOrEmpty(e.Data))
                {
                    _logger.LogWarning("soco-cli error: {Error}", e.Data);
                }
            };

            _serverProcess.Start();
            _serverProcess.BeginOutputReadLine();
            _serverProcess.BeginErrorReadLine();
            _startedAt = DateTime.UtcNow;

            _logger.LogInformation("Started soco-cli HTTP API server on port {Port}", _port);

            // Wait a moment for the server to start
            await Task.Delay(2000);

            return IsRunning();
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Failed to start soco-cli HTTP API server");
            return false;
        }
    }

    /// <summary>
    /// Stops the soco-cli HTTP API server
    /// </summary>
    public bool StopServer()
    {
        if (_serverProcess == null || _serverProcess.HasExited)
        {
            _logger.LogInformation("Soco-CLI server is not running");
            return true;
        }

        try
        {
            _serverProcess.Kill();
            _serverProcess.WaitForExit(5000);
            _serverProcess.Dispose();
            _serverProcess = null;
            _startedAt = null;

            _logger.LogInformation("Stopped soco-cli HTTP API server");
            return true;
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Failed to stop soco-cli HTTP API server");
            return false;
        }
    }

    /// <summary>
    /// Ensures the server is running, starting it if necessary
    /// </summary>
    public async Task<bool> EnsureServerRunningAsync()
    {
        if (IsRunning())
        {
            return true;
        }

        return await StartServerAsync();
    }
}
