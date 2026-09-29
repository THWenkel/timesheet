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

    [JsonPropertyName("username")]
    public string? Username { get; init; }

    [JsonPropertyName("is_admin")]
    public bool IsAdmin { get; init; }

    [JsonPropertyName("must_change_password")]
    public bool MustChangePassword { get; init; }

    [JsonPropertyName("has_password")]
    public bool HasPassword { get; init; }

    public string DisplayName => $"{Surname} {Lastname}";
}

// Username and IsAdmin: null means "leave unchanged".
public sealed record EmployeeDraft(
    string Surname,
    string Lastname,
    bool IsActive,
    string? Username = null,
    bool? IsAdmin = null);

public sealed class TemporaryPassword
{
    [JsonPropertyName("employee_id")]
    public int EmployeeId { get; init; }

    [JsonPropertyName("username")]
    public required string Username { get; init; }

    [JsonPropertyName("temporary_password")]
    public required string Password { get; init; }
}