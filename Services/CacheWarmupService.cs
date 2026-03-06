namespace YtDlpApi.Services;

/// <summary>
/// Background service that pre-warms yt-dlp's Node.js EJS engine on startup.
/// This ensures the first real user request doesn't pay the cold-start penalty.
/// </summary>
public class CacheWarmupService : BackgroundService
{
    private readonly IServiceProvider _services;
    private readonly ILogger<CacheWarmupService> _logger;

    public CacheWarmupService(IServiceProvider services, ILogger<CacheWarmupService> logger)
    {
        _services = services;
        _logger = logger;
    }

    protected override async Task ExecuteAsync(CancellationToken stoppingToken)
    {
        // Small delay to let the app fully start before hogging a semaphore slot
        await Task.Delay(TimeSpan.FromSeconds(2), stoppingToken);

        try
        {
            using var scope = _services.CreateScope();
            var ytdlp = _services.GetRequiredService<YtDlpService>();
            await ytdlp.PreWarmAsync();
        }
        catch (Exception ex)
        {
            _logger.LogWarning("Cache warmup failed: {Msg}", ex.Message);
        }
    }
}
