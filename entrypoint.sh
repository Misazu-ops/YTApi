#!/bin/bash
set -e

COOKIES_DIR="/app/cookies"
COOKIES_FILE="$COOKIES_DIR/cookies.txt"

mkdir -p "$COOKIES_DIR"

# Update yt-dlp to latest version
echo "📦 Updating yt-dlp..."
pip3 install --break-system-packages -U yt-dlp 2>/dev/null && echo "✅ yt-dlp updated" || echo "⚠️ yt-dlp update failed, using installed version"

# Export cookies from Firefox browser profile if mounted
if [ -d "/root/.mozilla/firefox" ]; then
    echo "🔑 Firefox profile found, exporting cookies..."
    yt-dlp --cookies-from-browser firefox --cookies "$COOKIES_FILE" --skip-download "https://www.youtube.com/watch?v=dQw4w9WgXcQ" 2>/dev/null && \
        echo "✅ Cookies exported to $COOKIES_FILE" || \
        echo "⚠️ Failed to export cookies from Firefox"
else
    echo "ℹ️ No Firefox profile mounted, skipping cookie export"
fi

if [ -f "$COOKIES_FILE" ]; then
    echo "🍪 Cookies file ready ($(wc -l < "$COOKIES_FILE") lines)"
else
    echo "⚠️ No cookies file available — some videos may fail"
fi

# Start the .NET app
echo "🚀 Starting .NET API..."
exec dotnet YtDlpApi.dll
