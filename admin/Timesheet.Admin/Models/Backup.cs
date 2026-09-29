using System.Text.Json.Serialization;

namespace Timesheet.Admin.Models;

public sealed class BackupTableInfo
{
    [JsonPropertyName("name")]
    public required string Name { get; init; }

    [JsonPropertyName("backup_table")]
    public required string BackupTable { get; init; }

    [JsonPropertyName("row_count")]
    public int RowCount { get; init; }

    [JsonPropertyName("backup_exists")]
    public bool BackupExists { get; init; }

    [JsonPropertyName("backup_row_count")]
    public int? BackupRowCount { get; init; }
}

public sealed class BackupTableResult
{
    [JsonPropertyName("table")]
    public required string Table { get; init; }

    [JsonPropertyName("rows")]
    public int Rows { get; init; }
}

public sealed class BackupDbResponse
{
    [JsonPropertyName("results")]
    public List<BackupTableResult> Results { get; init; } = [];
}

public sealed class RestoreTableResult
{
    [JsonPropertyName("table")]
    public required string Table { get; init; }

    [JsonPropertyName("source_rows")]
    public int SourceRows { get; init; }

    [JsonPropertyName("updated")]
    public int Updated { get; init; }

    [JsonPropertyName("inserted")]
    public int Inserted { get; init; }
}

public sealed class RestoreResponse
{
    [JsonPropertyName("dry_run")]
    public bool DryRun { get; init; }

    [JsonPropertyName("results")]
    public List<RestoreTableResult> Results { get; init; } = [];
}

/// <summary>A backup file chosen for import: which table, which format, its text.</summary>
public sealed record BackupFile(string Path, string Table, string Format, string Content);
