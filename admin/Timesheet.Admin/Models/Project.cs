using System.Text.Json.Serialization;

namespace Timesheet.Admin.Models;

public sealed class Project
{
    [JsonPropertyName("id")]
    public int Id { get; init; }

    [JsonPropertyName("name")]
    public required string Name { get; init; }

    [JsonPropertyName("description")]
    public required string Description { get; init; }

    [JsonPropertyName("customer_name")]
    public required string CustomerName { get; init; }

    [JsonPropertyName("purchase_number")]
    public required string PurchaseNumber { get; init; }

    [JsonPropertyName("unloading_point")]
    public required string UnloadingPoint { get; init; }

    [JsonPropertyName("consuming_plant")]
    public required string ConsumingPlant { get; init; }

    [JsonPropertyName("contact_person")]
    public required string ContactPerson { get; init; }

    [JsonPropertyName("contact_phone")]
    public required string ContactPhone { get; init; }

    [JsonPropertyName("contact_email")]
    public required string ContactEmail { get; init; }

    [JsonPropertyName("hourly_rate")]
    public decimal HourlyRate { get; init; }

    [JsonPropertyName("daily_rate")]
    public decimal DailyRate { get; init; }

    [JsonPropertyName("budget_amount")]
    public decimal BudgetAmount { get; init; }

    [JsonPropertyName("budget_unit")]
    public required string BudgetUnit { get; init; }

    [JsonPropertyName("starts_on")]
    public DateOnly StartsOn { get; init; }

    [JsonPropertyName("ends_on")]
    public DateOnly EndsOn { get; init; }

    [JsonPropertyName("status")]
    public required string Status { get; init; }

    [JsonPropertyName("employee_ids")]
    public required IReadOnlyList<int> EmployeeIds { get; init; }

    [JsonPropertyName("assigned_employees")]
    public required IReadOnlyList<string> AssignedEmployees { get; init; }

    public string BudgetDisplay => $"{BudgetAmount:N2} {(BudgetUnit == "hours" ? "Std." : "PT")}";
    public string RateDisplay => $"{HourlyRate:N2} €/Std. / {DailyRate:N2} €/Tag";
    public string AssignedEmployeesDisplay => string.Join(", ", AssignedEmployees);
    public string StatusDisplay => Status switch
    {
        "active" => "Aktiv",
        "paused" => "Pausiert",
        "completed" => "Abgeschlossen",
        _ => Status,
    };
}

public sealed record ProjectDraft(
    string Name,
    string Description,
    string CustomerName,
    string PurchaseNumber,
    string UnloadingPoint,
    string ConsumingPlant,
    string ContactPerson,
    string ContactPhone,
    string ContactEmail,
    decimal HourlyRate,
    decimal DailyRate,
    decimal BudgetAmount,
    string BudgetUnit,
    DateOnly StartsOn,
    DateOnly EndsOn,
    string Status,
    IReadOnlyList<int> EmployeeIds);

public sealed class Customer
{
    [JsonPropertyName("id")]
    public int Id { get; init; }

    [JsonPropertyName("name")]
    public required string Name { get; init; }

    [JsonPropertyName("notes")]
    public required string Notes { get; init; }

    [JsonPropertyName("street_1")]
    public required string Street1 { get; init; }

    [JsonPropertyName("street_2")]
    public required string Street2 { get; init; }

    [JsonPropertyName("postal_code")]
    public required string PostalCode { get; init; }

    [JsonPropertyName("city")]
    public required string City { get; init; }

    [JsonPropertyName("country")]
    public required string Country { get; init; }

    [JsonPropertyName("supplier_number")]
    public required string SupplierNumber { get; init; }

    [JsonPropertyName("contact_person")]
    public required string ContactPerson { get; init; }

    [JsonPropertyName("contact_phone")]
    public required string ContactPhone { get; init; }

    [JsonPropertyName("contact_email")]
    public required string ContactEmail { get; init; }

    [JsonPropertyName("is_active")]
    public bool IsActive { get; init; }

    [JsonPropertyName("updated_at")]
    public DateTime UpdatedAt { get; init; }
}

public sealed record CustomerDraft(
    string Name,
    string Notes,
    string Street1,
    string Street2,
    string PostalCode,
    string City,
    string Country,
    string SupplierNumber,
    string ContactPerson,
    string ContactPhone,
    string ContactEmail,
    bool IsActive);

public sealed class CountryCode2
{
    [JsonPropertyName("country_code")]
    public required string CountryCode { get; init; }

    [JsonPropertyName("country_name")]
    public required string CountryName { get; init; }

    public string DisplayName => $"{CountryCode} - {CountryName}";
}