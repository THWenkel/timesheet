using System.Net.Http;
using System.Net.Http.Json;
using System.Text.Json;
using Timesheet.Admin.Models;

namespace Timesheet.Admin.Services;

public interface IBackupApiClient
{
    Task<IReadOnlyList<BackupTableInfo>> GetTablesAsync(CancellationToken cancellationToken = default);
    Task<BackupDbResponse> BackupToDbAsync(IReadOnlyList<string> tables, CancellationToken cancellationToken = default);
    Task<byte[]> ExportAsync(string table, string format, CancellationToken cancellationToken = default);
    Task<RestoreResponse> RestoreFromDbAsync(IReadOnlyList<string> tables, bool confirm, bool dryRun, CancellationToken cancellationToken = default);
    Task<RestoreResponse> RestoreFromFileAsync(BackupFile file, bool confirm, bool dryRun, CancellationToken cancellationToken = default);
}

public sealed class BackupApiClient(HttpClient httpClient) : IBackupApiClient
{
    public async Task<IReadOnlyList<BackupTableInfo>> GetTablesAsync(
        CancellationToken cancellationToken = default)
    {
        using var response = await httpClient.GetAsync("api/backup/tables", cancellationToken);
        await EnsureSuccessAsync(response, cancellationToken);
        return await response.Content.ReadFromJsonAsync<List<BackupTableInfo>>(cancellationToken) ?? [];
    }

    public async Task<BackupDbResponse> BackupToDbAsync(
        IReadOnlyList<string> tables,
        CancellationToken cancellationToken = default)
    {
        using var response = await httpClient.PostAsJsonAsync(
            "api/backup/db", new { tables }, cancellationToken);
        await EnsureSuccessAsync(response, cancellationToken);
        return await response.Content.ReadFromJsonAsync<BackupDbResponse>(cancellationToken)
            ?? throw new InvalidOperationException("Die API hat kein Sicherungsergebnis geliefert.");
    }

    public async Task<byte[]> ExportAsync(
        string table,
        string format,
        CancellationToken cancellationToken = default)
    {
        using var response = await httpClient.GetAsync(
            $"api/backup/export/{Uri.EscapeDataString(table)}?format={format}",
            cancellationToken);
        await EnsureSuccessAsync(response, cancellationToken);
        return await response.Content.ReadAsByteArrayAsync(cancellationToken);
    }

    public async Task<RestoreResponse> RestoreFromDbAsync(
        IReadOnlyList<string> tables,
        bool confirm,
        bool dryRun,
        CancellationToken cancellationToken = default)
    {
        using var response = await httpClient.PostAsJsonAsync(
            "api/backup/restore/db",
            new { tables, confirm, dry_run = dryRun },
            cancellationToken);
        return await ReadRestoreAsync(response, cancellationToken);
    }

    public async Task<RestoreResponse> RestoreFromFileAsync(
        BackupFile file,
        bool confirm,
        bool dryRun,
        CancellationToken cancellationToken = default)
    {
        using var response = await httpClient.PostAsJsonAsync(
            "api/backup/restore/import",
            new { table = file.Table, format = file.Format, content = file.Content, confirm, dry_run = dryRun },
            cancellationToken);
        return await ReadRestoreAsync(response, cancellationToken);
    }

    private static async Task<RestoreResponse> ReadRestoreAsync(
        HttpResponseMessage response,
        CancellationToken cancellationToken)
    {
        await EnsureSuccessAsync(response, cancellationToken);
        return await response.Content.ReadFromJsonAsync<RestoreResponse>(cancellationToken)
            ?? throw new InvalidOperationException("Die API hat kein Wiederherstellungsergebnis geliefert.");
    }

    // Like EnsureSuccessStatusCode, but surfaces the "detail" message of the API.
    private static async Task EnsureSuccessAsync(
        HttpResponseMessage response,
        CancellationToken cancellationToken)
    {
        if (response.IsSuccessStatusCode)
        {
            return;
        }

        var detail = string.Empty;
        try
        {
            var body = await response.Content.ReadAsStringAsync(cancellationToken);
            using var document = JsonDocument.Parse(body);
            if (document.RootElement.TryGetProperty("detail", out var element))
            {
                detail = element.ToString();
            }
        }
        catch (JsonException)
        {
        }

        throw new HttpRequestException(
            string.IsNullOrEmpty(detail)
                ? $"HTTP {(int)response.StatusCode}"
                : $"HTTP {(int)response.StatusCode}: {detail}",
            null,
            response.StatusCode);
    }
}
