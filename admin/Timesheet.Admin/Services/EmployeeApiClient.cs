using System.Net.Http;
using System.Net.Http.Json;
using Timesheet.Admin.Models;

namespace Timesheet.Admin.Services;

public interface IEmployeeApiClient
{
    Task<IReadOnlyList<Employee>> GetAllAsync(CancellationToken cancellationToken = default);
    Task<Employee> CreateAsync(EmployeeDraft employee, CancellationToken cancellationToken = default);
    Task<Employee> UpdateAsync(int id, EmployeeDraft employee, CancellationToken cancellationToken = default);
    Task<TemporaryPassword> ResetPasswordAsync(int id, CancellationToken cancellationToken = default);
    Task DeleteAsync(int id, CancellationToken cancellationToken = default);
}

public sealed class EmployeeApiClient(HttpClient httpClient) : IEmployeeApiClient
{
    public async Task<IReadOnlyList<Employee>> GetAllAsync(
        CancellationToken cancellationToken = default)
    {
        return await httpClient.GetFromJsonAsync<List<Employee>>(
            "api/employees/admin?include_inactive=true",
            cancellationToken) ?? [];
    }

    public async Task<Employee> CreateAsync(
        EmployeeDraft employee,
        CancellationToken cancellationToken = default)
    {
        using var response = await httpClient.PostAsJsonAsync(
            "api/employees/",
            ToRequest(employee),
            cancellationToken);
        return await ReadResponseAsync(response, cancellationToken);
    }

    public async Task<Employee> UpdateAsync(
        int id,
        EmployeeDraft employee,
        CancellationToken cancellationToken = default)
    {
        using var response = await httpClient.PutAsJsonAsync(
            $"api/employees/{id}",
            ToRequest(employee),
            cancellationToken);
        return await ReadResponseAsync(response, cancellationToken);
    }

    public async Task DeleteAsync(int id, CancellationToken cancellationToken = default)
    {
        using var response = await httpClient.DeleteAsync($"api/employees/{id}", cancellationToken);
        if (response.IsSuccessStatusCode)
        {
            return;
        }

        // The API explains why (e.g. the user still has timesheet entries): show that text.
        var detail = string.Empty;
        try
        {
            using var document = System.Text.Json.JsonDocument.Parse(
                await response.Content.ReadAsStringAsync(cancellationToken));
            if (document.RootElement.TryGetProperty("detail", out var element))
            {
                detail = element.ToString();
            }
        }
        catch (System.Text.Json.JsonException)
        {
        }

        throw new InvalidOperationException(
            string.IsNullOrEmpty(detail) ? $"Löschen fehlgeschlagen (HTTP {(int)response.StatusCode})." : detail);
    }

    public async Task<TemporaryPassword> ResetPasswordAsync(
        int id,
        CancellationToken cancellationToken = default)
    {
        using var response = await httpClient.PostAsync(
            $"api/auth/admin/reset-password/{id}",
            content: null,
            cancellationToken);
        response.EnsureSuccessStatusCode();
        return await response.Content.ReadFromJsonAsync<TemporaryPassword>(cancellationToken)
            ?? throw new InvalidOperationException("Die API hat kein Einmalpasswort geliefert.");
    }

    private static object ToRequest(EmployeeDraft employee) => new
    {
        surname = employee.Surname.Trim(),
        lastname = employee.Lastname.Trim(),
        is_active = employee.IsActive,
        username = string.IsNullOrWhiteSpace(employee.Username) ? null : employee.Username.Trim(),
        is_admin = employee.IsAdmin,
    };

    private static async Task<Employee> ReadResponseAsync(
        HttpResponseMessage response,
        CancellationToken cancellationToken)
    {
        response.EnsureSuccessStatusCode();
        return await response.Content.ReadFromJsonAsync<Employee>(cancellationToken)
            ?? throw new InvalidOperationException("Die API hat keine Mitarbeiterdaten geliefert.");
    }
}