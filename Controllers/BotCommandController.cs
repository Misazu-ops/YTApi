using Telegram.Bot;
using TelegramBot.Builders;
using TelegramBot.Attributes;
using TelegramBot.Controllers;
using TelegramBot.Abstractions;
using Telegram.Bot.Types.ReplyMarkups;
using YtDlpApi.Services;

namespace YtDlpApi.Controllers;

public class BotCommandController(RedisTokenService _tokens, ILogger<BotCommandController> _logger) : BotControllerBase
{
    private const string GROUP = "nub_coder_s";
    private const string CHANNEL = "nub_coders";
    private const int DAILY_LIMIT = 1000;
    private const int ADMIN_LIMIT = 10000;

    [TextCommand("/start")]
    public async Task<IActionResult> HandleStart()
    {
        var userId = User.Id;
        _logger.LogInformation("Start command from user {UserId}", userId);

        var existingToken = await _tokens.GetUserToken(userId);
        string token;
        if (existingToken != null)
        {
            token = existingToken;
        }
        else
        {
            token = _tokens.GenerateToken();
            await _tokens.SetUserToken(userId, token);
        }

        var isAdmin = _tokens.IsAdmin(userId);
        var limit = isAdmin ? ADMIN_LIMIT : DAILY_LIMIT;

        var message =
            "🎬 Welcome to YT-DLP API Bot!\n\n" +
            $"👤 User ID: {userId}\n" +
            $"🔑 Your API Token: {token}\n" +
            $"📊 Daily Limit: {limit} requests\n" +
            (isAdmin ? "👑 Status: Admin\n" : "") +
            "\n" +
            "📡 API Base URL:\nhttps://api.nubcoder.com\n\n" +
            $"🔍 Search (FREE):\n/search?q=song+name&max_results=5\n\n" +
            $"📺 Video Info (Token Required):\n/info?q=URL_OR_QUERY&token={token}\n\n" +
            $"📈 Rate Limit Status:\n/rate-limit-status?token={token}\n\n" +
            "Use /menu for options | /help for docs";

        var keyboard = new KeyboardBuilder()
            .WithColumns(2)
            .AddButton("📊 Status", "/menu/status")
            .AddButton("🔑 Token", "/menu/token")
            .AddButton("🔄 Revoke", "/menu/revoke")
            .AddButton("❓ Help", "/menu/help")
            .Build();

        return Inline(message, keyboard);
    }

    [TextCommand("/menu")]
    public IActionResult HandleMenu()
    {
        var keyboard = new KeyboardBuilder()
            .WithColumns(2)
            .AddButton("📊 Status", "/menu/status")
            .AddButton("🔑 Token", "/menu/token")
            .AddButton("🔄 Revoke Token", "/menu/revoke")
            .AddButton("❓ Help", "/menu/help")
            .Build();

        return Inline("📋 Main Menu\n\nChoose an option:", keyboard);
    }

    [InlineCommand("/menu/status")]
    public async Task<IActionResult> HandleStatusInline()
    {
        return await GetStatusResult();
    }

    [TextCommand("/status")]
    public async Task<IActionResult> HandleStatus()
    {
        return await GetStatusResult();
    }

    private async Task<IActionResult> GetStatusResult()
    {
        var userId = User.Id;
        var existingToken = await _tokens.GetUserToken(userId);

        if (existingToken == null)
            return Text("❌ You don't have a token yet. Use /start to get one.");

        var used = await _tokens.GetUserRequestCount(userId);
        var isAdmin = _tokens.IsAdmin(userId);
        var limit = isAdmin ? ADMIN_LIMIT : DAILY_LIMIT;
        var remaining = Math.Max(0, limit - used);

        var message =
            "📊 Your Usage Statistics\n\n" +
            $"👤 User ID: {userId}\n" +
            $"🔑 Token: {existingToken}\n" +
            (isAdmin ? "👑 Status: Admin\n" : "👤 Status: User\n") +
            $"📈 Requests Used: {used}/{limit}\n" +
            $"📉 Remaining: {remaining}\n" +
            "🔄 Resets at midnight UTC";

        return Text(message);
    }

    [InlineCommand("/menu/token")]
    public async Task<IActionResult> HandleTokenInline()
    {
        return await GetTokenResult();
    }

    [TextCommand("/token")]
    public async Task<IActionResult> HandleToken()
    {
        return await GetTokenResult();
    }

    private async Task<IActionResult> GetTokenResult()
    {
        var userId = User.Id;
        var existingToken = await _tokens.GetUserToken(userId);

        if (existingToken == null)
            return Text("❌ You don't have a token yet. Use /start to get one.");

        return Text(
            "🔑 Your API Token\n\n" +
            $"{existingToken}\n\n" +
            $"Use it in API requests as ?token={existingToken}");
    }

    [InlineCommand("/menu/revoke")]
    public async Task<IActionResult> HandleRevokeInline()
    {
        return await GetRevokeResult();
    }

    [TextCommand("/revoke")]
    public async Task<IActionResult> HandleRevoke()
    {
        return await GetRevokeResult();
    }

    private async Task<IActionResult> GetRevokeResult()
    {
        var userId = User.Id;
        await _tokens.RevokeUserToken(userId);

        var newToken = _tokens.GenerateToken();
        await _tokens.SetUserToken(userId, newToken);

        return Text(
            "🔄 Token Revoked & Regenerated\n\n" +
            $"🔑 New Token: {newToken}\n\n" +
            "⚠️ Your old token no longer works.");
    }

    [InlineCommand("/menu/help")]
    public IActionResult HandleHelpInline()
    {
        return GetHelpResult();
    }

    [TextCommand("/help")]
    public IActionResult HandleHelp()
    {
        return GetHelpResult();
    }

    private IActionResult GetHelpResult()
    {
        var message =
            "❓ YT-DLP API Documentation\n\n" +
            "Endpoints:\n\n" +
            "🔍 GET /search\n" +
            "Free search, no token needed\n" +
            "Params: q (query), max_results (1-20)\n\n" +
            "📺 GET /info\n" +
            "Get video info with streaming URL\n" +
            "Params: q (URL or query), token, max_results\n\n" +
            "📈 GET /rate-limit-status\n" +
            "Check your usage stats\n" +
            "Params: token\n\n" +
            "❤️ GET /health\n" +
            "API health check\n\n" +
            $"Limits: {DAILY_LIMIT}/day (users) | {ADMIN_LIMIT}/day (admins)\n\n" +
            $"💬 Group: @{GROUP}\n" +
            $"📢 Channel: @{CHANNEL}";

        return Text(message);
    }
}
