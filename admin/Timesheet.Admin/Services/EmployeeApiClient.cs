using System.Net.Http;
using System.Net.Http.Json;
using Timesheet.Admin.Models;

namespace Timesheet.Admin.Services;

public interface IEmployeeApiClient
{
    Task<IReadOnlyList<Employee>> GetAllAsync(CancellationToken cancellationToken = default);
    Task<Employee> CreateAsync(EmployeeDraft employee, CancellationToken cancellationToken = default);
    Task<Employee> UpdateAsync(int id, EmployeeDraft employee, CancellationToken cancellationToken = default);
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

    private static object ToRequest(EmployeeDraft employee) => new
    {
        surname = employee.Surname.Trim(),
        lastname = employee.Lastname.Trim(),
        is_active = employee.IsActive,
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