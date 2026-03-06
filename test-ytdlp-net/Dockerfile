FROM mcr.microsoft.com/dotnet/sdk:8.0
WORKDIR /app

# Install yt-dlp, deno, ffmpeg
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 python3-pip ffmpeg curl unzip ca-certificates \
    && pip3 install --break-system-packages "yt-dlp[default]" \
    && curl -fsSL https://deno.land/install.sh | sh \
    && mv /root/.deno/bin/deno /usr/local/bin/deno \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

COPY TestYtdlp.csproj ./
RUN dotnet restore

COPY Program.cs ./
RUN dotnet build -c Release -o /app/out

ENTRYPOINT ["dotnet", "/app/out/TestYtdlp.dll"]
