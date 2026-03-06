using System.Net;
using System.Text;
using System.Text.Json;

namespace YtDlpApi.Services;

/// <summary>
/// Fast YouTube metadata service using publicly available YouTube APIs.
/// 
/// Strategy (all work despite bot-flagged server IPs):
/// - oEmbed API (~0.4s): title, author, thumbnail
/// - InnerTube search API (~0.6s): title, duration, views, channel, thumbnail
/// - InnerTube next API (~0.8s): title, views, channel (backup)
/// 
/// For URL queries: oEmbed ∥ InnerTube search (by title) → merge results  
/// For search queries: InnerTube search directly
/// </summary>
public class InnerTubeService
{
    private readonly HttpClient _http;
    private readonly ILogger<InnerTubeService> _logger;

    private const string SearchEndpoint = "https://www.youtube.com/youtubei/v1/search?prettyPrint=false";
    private const string NextEndpoint = "https://www.youtube.com/youtubei/v1/next?prettyPrint=false";
    private const string OEmbedEndpoint = "https://www.youtube.com/oembed";
    private const string ClientVersion = "2.20250305.01.00";
    private const string UserAgent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36";

    public InnerTubeService(ILogger<InnerTubeService> logger)
    {
        _logger = logger;

        var handler = new HttpClientHandler
        {
            AutomaticDecompression = DecompressionMethods.GZip | DecompressionMethods.Deflate
        };

        _http = new HttpClient(handler) { Timeout = TimeSpan.FromSeconds(10) };
        _http.DefaultRequestHeaders.Add("User-Agent", UserAgent);
    }

    // ═══════════════════════════════════════════════════════════════
    //  VIDEO METADATA — for URL-based queries
    // ═══════════════════════════════════════════════════════════════

    /// <summary>
    /// Get video metadata using oEmbed + InnerTube next in parallel.
    /// Returns complete metadata (title, author, duration, views, thumbnail) in ~0.8s.
    /// </summary>
    public async Task<VideoInfo?> GetVideoMetadataAsync(string videoId, CancellationToken ct = default)
    {
        try
        {
            // Run oEmbed + InnerTube next in parallel
            var oembedTask = GetOEmbedAsync(videoId, ct);
            var nextTask = GetNextMetadataAsync(videoId, ct);

            await Task.WhenAll(oembedTask, nextTask);

            var oembed = oembedTask.Result;
            var next = nextTask.Result;

            if (oembed == null && next == null) return null;

            // Merge: oEmbed is authoritative for title/author/thumbnail,
            // next provides views
            var info = new VideoInfo
            {
                VideoId = videoId,
                WebpageUrl = $"https://www.youtube.com/watch?v={videoId}",
                Title = oembed?.Title ?? next?.Title ?? "",
                Uploader = oembed?.Author ?? next?.Channel ?? "",
                Thumbnail = oembed?.Thumbnail ?? $"https://i.ytimg.com/vi/{videoId}/hqdefault.jpg",
                ViewCount = next?.Views ?? 0,
                Duration = 0, // Will be populated by yt-dlp background
                StreamUrl = "",
                HttpHeaders = new Dictionary<string, string>
                {
                    ["User-Agent"] = UserAgent,
                    ["Accept"] = "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                    ["Accept-Language"] = "en-us,en;q=0.5",
                    ["Sec-Fetch-Mode"] = "navigate"
                }
            };

            if (string.IsNullOrEmpty(info.Title)) return null;
            return info;
        }
        catch (Exception ex)
        {
            _logger.LogWarning("GetVideoMetadata failed for {VideoId}: {Msg}", videoId, ex.Message);
            return null;
        }
    }

    // ─── oEmbed ───
    private async Task<OEmbedResult?> GetOEmbedAsync(string videoId, CancellationToken ct)
    {
        try
        {
            var url = $"{OEmbedEndpoint}?url=https://www.youtube.com/watch?v={videoId}&format=json";
            var json = await _http.GetStringAsync(url, ct);
            using var doc = JsonDocument.Parse(json);
            var root = doc.RootElement;

            return new OEmbedResult
            {
                Title = root.TryGetProperty("title", out var t) ? t.GetString() ?? "" : "",
                Author = root.TryGetProperty("author_name", out var a) ? a.GetString() ?? "" : "",
                Thumbnail = root.TryGetProperty("thumbnail_url", out var th) ? th.GetString() ?? "" : ""
            };
        }
        catch (Exception ex)
        {
            _logger.LogDebug("oEmbed failed for {VideoId}: {Msg}", videoId, ex.Message);
            return null;
        }
    }

    // ─── InnerTube /next ───
    private async Task<NextResult?> GetNextMetadataAsync(string videoId, CancellationToken ct)
    {
        try
        {
            var payload = JsonSerializer.Serialize(new
            {
                context = new
                {
                    client = new
                    {
                        clientName = "WEB",
                        clientVersion = ClientVersion,
                        hl = "en",
                        gl = "US"
                    }
                },
                videoId = videoId
            });

            var response = await _http.PostAsync(NextEndpoint,
                new StringContent(payload, Encoding.UTF8, "application/json"), ct);
            var json = await response.Content.ReadAsStringAsync(ct);

            using var doc = JsonDocument.Parse(json);
            var root = doc.RootElement;

            var result = new NextResult();

            // Navigate: contents.twoColumnWatchNextResults.results.results.contents[]
            if (!root.TryGetProperty("contents", out var contents)) return null;
            if (!contents.TryGetProperty("twoColumnWatchNextResults", out var twoCol)) return null;
            if (!twoCol.TryGetProperty("results", out var results)) return null;
            if (!results.TryGetProperty("results", out var innerResults)) return null;
            if (!innerResults.TryGetProperty("contents", out var contentsList)) return null;

            foreach (var item in contentsList.EnumerateArray())
            {
                if (item.TryGetProperty("videoPrimaryInfoRenderer", out var vpi))
                {
                    // Title
                    if (vpi.TryGetProperty("title", out var titleObj) && titleObj.TryGetProperty("runs", out var runs))
                    {
                        var sb = new StringBuilder();
                        foreach (var run in runs.EnumerateArray())
                            sb.Append(run.TryGetProperty("text", out var txt) ? txt.GetString() : "");
                        result.Title = sb.ToString();
                    }

                    // Views
                    if (vpi.TryGetProperty("viewCount", out var viewCount)
                        && viewCount.TryGetProperty("videoViewCountRenderer", out var vvcr)
                        && vvcr.TryGetProperty("viewCount", out var vc)
                        && vc.TryGetProperty("simpleText", out var viewText))
                    {
                        var cleaned = new string(viewText.GetString()?.Where(c => char.IsDigit(c)).ToArray() ?? Array.Empty<char>());
                        if (long.TryParse(cleaned, out var views))
                            result.Views = views;
                    }
                }

                if (item.TryGetProperty("videoSecondaryInfoRenderer", out var vsi))
                {
                    // Channel
                    if (vsi.TryGetProperty("owner", out var owner)
                        && owner.TryGetProperty("videoOwnerRenderer", out var vor)
                        && vor.TryGetProperty("title", out var chTitle)
                        && chTitle.TryGetProperty("runs", out var chRuns)
                        && chRuns.GetArrayLength() > 0)
                    {
                        result.Channel = chRuns[0].TryGetProperty("text", out var chText) ? chText.GetString() ?? "" : "";
                    }
                }
            }

            return string.IsNullOrEmpty(result.Title) ? null : result;
        }
        catch (Exception ex)
        {
            _logger.LogDebug("InnerTube next failed for {VideoId}: {Msg}", videoId, ex.Message);
            return null;
        }
    }

    // ═══════════════════════════════════════════════════════════════
    //  SEARCH — InnerTube search API
    // ═══════════════════════════════════════════════════════════════

    /// <summary>
    /// Search YouTube via InnerTube search API (~0.6s).
    /// Returns search results with title, channel, duration, views, thumbnail.
    /// </summary>
    public async Task<List<SearchResult>> SearchAsync(string query, int maxResults = 5, CancellationToken ct = default)
    {
        var results = new List<SearchResult>();
        try
        {
            var payload = JsonSerializer.Serialize(new
            {
                context = new
                {
                    client = new
                    {
                        clientName = "WEB",
                        clientVersion = ClientVersion,
                        hl = "en",
                        gl = "US"
                    }
                },
                query = query
            });

            var response = await _http.PostAsync(SearchEndpoint,
                new StringContent(payload, Encoding.UTF8, "application/json"), ct);
            var json = await response.Content.ReadAsStringAsync(ct);

            using var doc = JsonDocument.Parse(json);
            var root = doc.RootElement;

            if (!root.TryGetProperty("contents", out var contents)) return results;
            if (!contents.TryGetProperty("twoColumnSearchResultsRenderer", out var twoCol)) return results;
            if (!twoCol.TryGetProperty("primaryContents", out var primary)) return results;
            if (!primary.TryGetProperty("sectionListRenderer", out var slr)) return results;
            if (!slr.TryGetProperty("contents", out var sections)) return results;

            foreach (var section in sections.EnumerateArray())
            {
                if (results.Count >= maxResults) break;
                if (!section.TryGetProperty("itemSectionRenderer", out var isr)) continue;
                if (!isr.TryGetProperty("contents", out var items)) continue;

                foreach (var item in items.EnumerateArray())
                {
                    if (results.Count >= maxResults) break;
                    if (!item.TryGetProperty("videoRenderer", out var vr)) continue;

                    var videoId = vr.TryGetProperty("videoId", out var vid) ? vid.GetString() ?? "" : "";
                    if (string.IsNullOrEmpty(videoId)) continue;

                    var title = "";
                    if (vr.TryGetProperty("title", out var titleObj) && titleObj.TryGetProperty("runs", out var runs))
                    {
                        var sb = new StringBuilder();
                        foreach (var run in runs.EnumerateArray())
                            sb.Append(run.TryGetProperty("text", out var txt) ? txt.GetString() : "");
                        title = sb.ToString();
                    }

                    var channel = "";
                    if (vr.TryGetProperty("ownerText", out var ot) && ot.TryGetProperty("runs", out var oRuns) && oRuns.GetArrayLength() > 0)
                        channel = oRuns[0].TryGetProperty("text", out var chTxt) ? chTxt.GetString() ?? "" : "";

                    var durationText = "";
                    if (vr.TryGetProperty("lengthText", out var lt) && lt.TryGetProperty("simpleText", out var ltTxt))
                        durationText = ltTxt.GetString() ?? "";

                    var viewText = "";
                    if (vr.TryGetProperty("viewCountText", out var vct) && vct.TryGetProperty("simpleText", out var vctTxt))
                        viewText = vctTxt.GetString() ?? "";

                    var thumbnail = $"https://i.ytimg.com/vi/{videoId}/hqdefault.jpg";
                    if (vr.TryGetProperty("thumbnail", out var th) && th.TryGetProperty("thumbnails", out var thumbs) && thumbs.GetArrayLength() > 0)
                    {
                        var lastThumb = thumbs[thumbs.GetArrayLength() - 1];
                        if (lastThumb.TryGetProperty("url", out var tu))
                            thumbnail = tu.GetString() ?? thumbnail;
                    }

                    results.Add(new SearchResult
                    {
                        VideoId = videoId,
                        Title = title,
                        ChannelName = channel,
                        DurationText = durationText,
                        Duration = ParseDuration(durationText),
                        ViewsText = viewText,
                        Views = ParseViews(viewText),
                        Thumbnail = thumbnail,
                        YoutubeLink = $"https://www.youtube.com/watch?v={videoId}"
                    });
                }
            }

            return results;
        }
        catch (Exception ex)
        {
            _logger.LogWarning("InnerTube search failed for '{Query}': {Msg}", query, ex.Message);
            return results;
        }
    }

    // ═══════════════════════════════════════════════════════════════
    //  Helpers
    // ═══════════════════════════════════════════════════════════════

    private static int ParseDuration(string text)
    {
        if (string.IsNullOrEmpty(text)) return 0;
        var parts = text.Split(':');
        try
        {
            return parts.Length switch
            {
                1 => int.Parse(parts[0]),
                2 => int.Parse(parts[0]) * 60 + int.Parse(parts[1]),
                3 => int.Parse(parts[0]) * 3600 + int.Parse(parts[1]) * 60 + int.Parse(parts[2]),
                _ => 0
            };
        }
        catch { return 0; }
    }

    private static long ParseViews(string text)
    {
        if (string.IsNullOrEmpty(text)) return 0;
        var cleaned = new string(text.Where(c => char.IsDigit(c)).ToArray());
        return long.TryParse(cleaned, out var v) ? v : 0;
    }

    // ─── Internal DTOs ───
    private class OEmbedResult
    {
        public string Title { get; set; } = "";
        public string Author { get; set; } = "";
        public string Thumbnail { get; set; } = "";
    }

    private class NextResult
    {
        public string Title { get; set; } = "";
        public string Channel { get; set; } = "";
        public long Views { get; set; }
    }
}

public class SearchResult
{
    public string VideoId { get; set; } = "";
    public string Title { get; set; } = "";
    public string ChannelName { get; set; } = "";
    public string DurationText { get; set; } = "";
    public int Duration { get; set; }
    public string ViewsText { get; set; } = "";
    public long Views { get; set; }
    public string Thumbnail { get; set; } = "";
    public string YoutubeLink { get; set; } = "";
}
