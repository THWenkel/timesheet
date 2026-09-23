using System.Text.Json.Serialization;

namespace Timesheet.Admin.Models;

public sealed class Employee
{
    [JsonPropertyName("id")]
    public int Id { get; init; }

    [JsonPropertyName("surname")]
    public required string Surname { get; init; }

    [JsonPropertyName("lastname")]
    public required string Lastname { get; init; }

    [JsonPropertyName("is_active")]
    public bool IsActive { get; init; }

    [JsonPropertyName("updated_at")]
    public DateTime UpdatedAt { get; init; }

    public string DisplayName => $"{Surname} {Lastname}";
}

public sealed record EmployeeDraft(string Surname, string Lastname, bool IsActive);