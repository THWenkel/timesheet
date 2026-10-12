using System.IO;
using System.Text.Json;

namespace Timesheet.Admin.Services;

public enum ApiUrlSource
{
    None,
    Environment,
    User,
    ConfigFile,
}

public sealed record ApiUrlChoice(string? Url, ApiUrlSource Source);

/// <summary>
/// Where the admin tool finds the API backend. There is deliberately no built-in default:
/// the backend runs on a server, not on the PC of the administrator. Order of precedence:
/// 1. environment variable TIMESHEET_API_URL,
/// 2. the address chosen in the server settings dialog (%APPDATA%\Timesheet.Admin\settings.json),
/// 3. "ApiUrl" in appsettings.json next to the program (for rolling out one address to many PCs).
/// </summary>
public static class ApiEndpoint
{
    public const string EnvironmentVariable = "TIMESHEET_API_URL";
    public const string ConfigFileName = "appsettings.json";

    public static ApiUrlChoice Resolve(ISettingsService settings)
    {
        var fromEnvironment = Environment.GetEnvironmentVariable(EnvironmentVariable);
        if (!string.IsNullOrWhiteSpace(fromEnvironment))
        {
            return new ApiUrlChoice(fromEnvironment.Trim(), ApiUrlSource.Environment);
        }

        var fromUser = settings.Load().ApiUrl;
        if (!string.IsNullOrWhiteSpace(fromUser))
        {
            return new ApiUrlChoice(fromUser.Trim(), ApiUrlSource.User);
        }

        var fromFile = ReadConfigFileUrl();
        return string.IsNullOrWhiteSpace(fromFile)
            ? new ApiUrlChoice(null, ApiUrlSource.None)
            : new ApiUrlChoice(fromFile.Trim(), ApiUrlSource.ConfigFile);
    }

    /// <summary>Accepts only absolute http(s) addresses and makes sure of the trailing slash.</summary>
    public static bool TryNormalize(string? text, out Uri uri)
    {
        uri = null!;
        var trimmed = text?.Trim();
        if (string.IsNullOrEmpty(trimmed)
            || !Uri.TryCreate(trimmed, UriKind.Absolute, out var parsed)
            || (parsed.Scheme != Uri.UriSchemeHttp && parsed.Scheme != Uri.UriSchemeHttps)
            || string.IsNullOrEmpty(parsed.Host))
        {
            return false;
        }

        var builder = new UriBuilder(parsed) { Query = string.Empty, Fragment = string.Empty };
        if (!builder.Path.EndsWith('/'))
        {
            builder.Path += '/';
        }

        uri = builder.Uri;
        return true;
    }

    public static string DescribeSource(ApiUrlSource source) => source switch
    {
        ApiUrlSource.Environment => $"Umgebungsvariable {EnvironmentVariable}",
        ApiUrlSource.User => "Einstellung dieses Benutzers",
        ApiUrlSource.ConfigFile => $"Datei {ConfigFileName}",
        _ => "nicht eingestellt",
    };

    private static string? ReadConfigFileUrl()
    {
        try
        {
            var path = Path.Combine(AppContext.BaseDirectory, ConfigFileName);
            if (!File.Exists(path))
            {
                return null;
            }

            using var document = JsonDocument.Parse(
                File.ReadAllText(path),
                new JsonDocumentOptions { CommentHandling = JsonCommentHandling.Skip, AllowTrailingCommas = true });
            return document.RootElement.TryGetProperty("ApiUrl", out var value)
                && value.ValueKind == JsonValueKind.String
                    ? value.GetString()
                    : null;
        }
        catch (Exception exception) when (exception is IOException or JsonException or UnauthorizedAccessException)
        {
            return null;
        }
    }
}
