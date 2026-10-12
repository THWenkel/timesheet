using System.Net;
using System.Net.Http;
using System.Net.Http.Json;
using System.Text.Json;
using System.Text.Json.Serialization;

namespace Timesheet.Admin.Services;

public sealed class CurrentUser
{
    [JsonPropertyName("id")]
    public int Id { get; init; }

    [JsonPropertyName("username")]
    public required string Username { get; init; }

    [JsonPropertyName("display_name")]
    public required string DisplayName { get; init; }

    [JsonPropertyName("is_admin")]
    public bool IsAdmin { get; init; }

    [JsonPropertyName("must_change_password")]
    public bool MustChangePassword { get; init; }
}

/// <summary>Result of a login or password change: the user, or a message to show.</summary>
public sealed record AuthResult(CurrentUser? User, string? Error);

public interface IAuthApiClient
{
    /// <summary>Null if the address points to a reachable Timesheet API, otherwise a message.</summary>
    Task<string?> CheckConnectionAsync(CancellationToken cancellationToken = default);
    Task<bool> IsAuthEnabledAsync(CancellationToken cancellationToken = default);
    Task<AuthResult> LoginAsync(string username, string password, CancellationToken cancellationToken = default);
    Task<AuthResult> ChangePasswordAsync(string currentPassword, string newPassword, CancellationToken cancellationToken = default);
}

public sealed class AuthApiClient(HttpClient httpClient) : IAuthApiClient
{
    public async Task<string?> CheckConnectionAsync(CancellationToken cancellationToken = default)
    {
        using var timeout = CancellationTokenSource.CreateLinkedTokenSource(cancellationToken);
        timeout.CancelAfter(TimeSpan.FromSeconds(10));
        try
        {
            using var response = await httpClient.GetAsync("api/auth/config", timeout.Token);
            if (!response.IsSuccessStatusCode)
            {
                return $"Der Server antwortet mit Status {(int)response.StatusCode}. "
                    + "Ist die Adresse vollständig, z. B. mit dem Pfad /timesheet/?";
            }

            using var document = JsonDocument.Parse(
                await response.Content.ReadAsStringAsync(timeout.Token));
            return document.RootElement.TryGetProperty("auth_enabled", out _)
                ? null
                : "Die Adresse antwortet, ist aber nicht das Timesheet-API.";
        }
        catch (OperationCanceledException) when (!cancellationToken.IsCancellationRequested)
        {
            return "Zeitüberschreitung: Der Server antwortet nicht.";
        }
        catch (JsonException)
        {
            return "Die Adresse antwortet, ist aber nicht das Timesheet-API (keine gültige Antwort).";
        }
        catch (HttpRequestException exception)
        {
            return "Der Server ist nicht erreichbar: "
                + (exception.InnerException?.Message ?? exception.Message);
        }
    }

    // Unreachable API counts as "enabled": the login dialog then shows the connection error.
    public async Task<bool> IsAuthEnabledAsync(CancellationToken cancellationToken = default)
    {
        try
        {
            using var response = await httpClient.GetAsync("api/auth/config", cancellationToken);
            if (!response.IsSuccessStatusCode)
            {
                return true;
            }

            using var document = JsonDocument.Parse(
                await response.Content.ReadAsStringAsync(cancellationToken));
            return !document.RootElement.TryGetProperty("auth_enabled", out var enabled)
                || enabled.GetBoolean();
        }
        catch (Exception exception) when (exception is HttpRequestException or JsonException)
        {
            return true;
        }
    }

    public Task<AuthResult> LoginAsync(
        string username,
        string password,
        CancellationToken cancellationToken = default) =>
        SendAsync("api/auth/login", new { username, password }, cancellationToken);

    public Task<AuthResult> ChangePasswordAsync(
        string currentPassword,
        string newPassword,
        CancellationToken cancellationToken = default) =>
        SendAsync(
            "api/auth/change-password",
            new { current_password = currentPassword, new_password = newPassword },
            cancellationToken);

    private async Task<AuthResult> SendAsync(
        string path,
        object body,
        CancellationToken cancellationToken)
    {
        try
        {
            using var response = await httpClient.PostAsJsonAsync(path, body, cancellationToken);
            if (response.IsSuccessStatusCode)
            {
                var user = await response.Content.ReadFromJsonAsync<CurrentUser>(cancellationToken);
                return new AuthResult(user, user is null ? "Leere Antwort der API." : null);
            }

            return new AuthResult(null, await ReadDetailAsync(response, cancellationToken));
        }
        catch (HttpRequestException exception)
        {
            return new AuthResult(null, $"Die Timesheet-API ist nicht erreichbar: {exception.Message}");
        }
    }

    private static async Task<string> ReadDetailAsync(
        HttpResponseMessage response,
        CancellationToken cancellationToken)
    {
        try
        {
            using var document = JsonDocument.Parse(
                await response.Content.ReadAsStringAsync(cancellationToken));
            if (document.RootElement.TryGetProperty("detail", out var detail)
                && detail.ValueKind == JsonValueKind.String)
            {
                return detail.GetString()!;
            }
        }
        catch (JsonException)
        {
        }

        return response.StatusCode == HttpStatusCode.Unauthorized
            ? "Anmeldung fehlgeschlagen."
            : $"HTTP {(int)response.StatusCode}";
    }
}
