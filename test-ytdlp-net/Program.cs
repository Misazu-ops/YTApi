using YtdlpNET;

Console.WriteLine("=== Ytdlp.NET Test ===\n");

var ytdlp = new Ytdlp();

// Test 1: Version check
Console.WriteLine("[1] Checking yt-dlp version...");
try
{
    var version = await ytdlp.GetVersionAsync();
    Console.WriteLine($"    yt-dlp version: {version}");
}
catch (Exception ex)
{
    Console.WriteLine($"    Error: {ex.Message}");
}

// Test 2: Get metadata for a video  
Console.WriteLine("\n[2] Fetching metadata for: https://youtu.be/_sFBA6icLMo");
try
{
    var ytdlp2 = new Ytdlp();
    ytdlp2.UseCookies("/app/cookies/cookies.txt");
    
    Console.WriteLine("    Trying GetFormatsDetailedAsync...");
    var formats = await ytdlp2.GetFormatsDetailedAsync("https://youtu.be/_sFBA6icLMo");
    Console.WriteLine($"    Formats count: {formats?.Count ?? 0}");
    
    if (formats != null && formats.Count > 0)
    {
        foreach (var f in formats.Take(3))
        {
            Console.WriteLine($"    Format: {f}");
        }
    }
}
catch (Exception ex)
{
    Console.WriteLine($"    Error: {ex.Message}");
}

// Test 2b: Metadata for a public video (no cookies)
Console.WriteLine("\n[2b] Metadata for Rick Astley (no cookies needed)...");
try
{
    var ytdlp2b = new Ytdlp();
    var metadata = await ytdlp2b.GetVideoMetadataJsonAsync("https://youtu.be/dQw4w9WgXcQ");
    if (metadata != null)
    {
        Console.WriteLine($"    Title:    {metadata.Title}");
        Console.WriteLine($"    Duration: {metadata.Duration}s");
        Console.WriteLine($"    Views:    {metadata.ViewCount:N0}");
        Console.WriteLine($"    Formats:  {metadata.Formats?.Count ?? 0}");
        
        var bestFmt = metadata.Formats?
            .Where(f => f.Vcodec != "none" && f.Acodec != "none")
            .Where(f => f.Protocol?.StartsWith("http") == true)
            .OrderByDescending(f => f.Height ?? 0)
            .FirstOrDefault();
        if (bestFmt != null)
        {
            Console.WriteLine($"    Best:     {bestFmt.FormatId} {bestFmt.Resolution} ({bestFmt.Ext})");
            Console.WriteLine($"    URL:      {bestFmt.Url?[..Math.Min(120, bestFmt.Url?.Length ?? 0)]}...");
        }
    }
    else
    {
        Console.WriteLine("    metadata is null");
    }
}
catch (Exception ex)
{
    Console.WriteLine($"    Error: {ex.Message}");
}

// Test 3: Simple metadata (fast)
Console.WriteLine("\n[3] Quick metadata test (GetSimpleMetadataAsync)...");
try
{
    var ytdlp3 = new Ytdlp();
    ytdlp3.UseCookies("/app/cookies/cookies.txt");

    var simple = await ytdlp3.GetSimpleMetadataAsync("https://youtu.be/_sFBA6icLMo");
    if (simple != null)
    {
        Console.WriteLine($"    Title: {simple.Title}");
        Console.WriteLine($"    ID:    {simple.Id}");
    }
}
catch (Exception ex)
{
    Console.WriteLine($"    Error: {ex.Message}");
}

Console.WriteLine("\n=== Done ===");
