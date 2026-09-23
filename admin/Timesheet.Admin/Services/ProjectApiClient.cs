using System.Net.Http;
using System.Net.Http.Json;
using Timesheet.Admin.Models;

namespace Timesheet.Admin.Services;

public interface IProjectApiClient
{
    Task<IReadOnlyList<Project>> GetAllAsync(CancellationToken cancellationToken = default);
    Task<IReadOnlyList<Project>> GetForEmployeeAsync(
        int employeeId,
        CancellationToken cancellationToken = default);
    Task<IReadOnlyList<Customer>> GetCustomersAsync(CancellationToken cancellationToken = default);
    Task<IReadOnlyList<Customer>> GetAllCustomersAsync(
        CancellationToken cancellationToken = default);
    Task<IReadOnlyList<CountryCode2>> GetCountryCodesAsync(
        CancellationToken cancellationToken = default);
    Task<Customer> CreateCustomerAsync(
        CustomerDraft customer,
        CancellationToken cancellationToken = default);
    Task<Customer> UpdateCustomerAsync(
        int id,
        CustomerDraft customer,
        CancellationToken cancellationToken = default);
    Task<Project> CreateAsync(ProjectDraft project, CancellationToken cancellationToken = default);
    Task<Project> UpdateAsync(
        int id,
        ProjectDraft project,
        CancellationToken cancellationToken = default);
}

public sealed class ProjectApiClient(HttpClient httpClient) : IProjectApiClient
{
    public async Task<IReadOnlyList<Project>> GetAllAsync(
        CancellationToken cancellationToken = default) =>
        await httpClient.GetFromJsonAsync<List<Project>>("api/projects/", cancellationToken) ?? [];

    public async Task<IReadOnlyList<Project>> GetForEmployeeAsync(
        int employeeId,
        CancellationToken cancellationToken = default) =>
        await httpClient.GetFromJsonAsync<List<Project>>(
            $"api/projects/?employee_id={employeeId}", cancellationToken) ?? [];

    public async Task<IReadOnlyList<Customer>> GetCustomersAsync(
        CancellationToken cancellationToken = default) =>
        await httpClient.GetFromJsonAsync<List<Customer>>("api/customers/", cancellationToken) ?? [];

    public async Task<IReadOnlyList<Customer>> GetAllCustomersAsync(
        CancellationToken cancellationToken = default) =>
        await httpClient.GetFromJsonAsync<List<Customer>>(
            "api/customers/?include_inactive=true", cancellationToken) ?? [];

    public async Task<IReadOnlyList<CountryCode2>> GetCountryCodesAsync(
        CancellationToken cancellationToken = default) =>
        await httpClient.GetFromJsonAsync<List<CountryCode2>>(
            "api/country-codes/", cancellationToken) ?? [];

    public async Task<Customer> CreateCustomerAsync(
        CustomerDraft customer,
        CancellationToken cancellationToken = default)
    {
        using var response = await httpClient.PostAsJsonAsync(
            "api/customers/", ToRequest(customer), cancellationToken);
        return await ReadCustomerResponseAsync(response, cancellationToken);
    }

    public async Task<Customer> UpdateCustomerAsync(
        int id,
        CustomerDraft customer,
        CancellationToken cancellationToken = default)
    {
        using var response = await httpClient.PutAsJsonAsync(
            $"api/customers/{id}", ToRequest(customer), cancellationToken);
        return await ReadCustomerResponseAsync(response, cancellationToken);
    }

    public async Task<Project> CreateAsync(
        ProjectDraft project,
        CancellationToken cancellationToken = default)
    {
        using var response = await httpClient.PostAsJsonAsync(
            "api/projects/", ToRequest(project), cancellationToken);
        return await ReadResponseAsync(response, cancellationToken);
    }

    public async Task<Project> UpdateAsync(
        int id,
        ProjectDraft project,
        CancellationToken cancellationToken = default)
    {
        using var response = await httpClient.PutAsJsonAsync(
            $"api/projects/{id}", ToRequest(project), cancellationToken);
        return await ReadResponseAsync(response, cancellationToken);
    }

    private static object ToRequest(ProjectDraft project) => new
    {
        name = project.Name.Trim(),
        description = project.Description.Trim(),
        customer_name = project.CustomerName.Trim(),
        purchase_number = project.PurchaseNumber.Trim(),
        unloading_point = project.UnloadingPoint.Trim(),
        consuming_plant = project.ConsumingPlant.Trim(),
        contact_person = project.ContactPerson.Trim(),
        contact_phone = project.ContactPhone.Trim(),
        contact_email = project.ContactEmail.Trim(),
        hourly_rate = project.HourlyRate,
        daily_rate = project.DailyRate,
        budget_amount = project.BudgetAmount,
        budget_unit = project.BudgetUnit,
        starts_on = project.StartsOn,
        ends_on = project.EndsOn,
        status = project.Status,
        employee_ids = project.EmployeeIds,
    };

    private static object ToRequest(CustomerDraft customer) => new
    {
        name = customer.Name.Trim(),
        notes = customer.Notes.Trim(),
        street_1 = customer.Street1.Trim(),
        street_2 = customer.Street2.Trim(),
        postal_code = customer.PostalCode.Trim(),
        city = customer.City.Trim(),
        country = customer.Country.Trim(),
        supplier_number = customer.SupplierNumber.Trim(),
        contact_person = customer.ContactPerson.Trim(),
        contact_phone = customer.ContactPhone.Trim(),
        contact_email = customer.ContactEmail.Trim(),
        is_active = customer.IsActive,
    };

    private static async Task<Project> ReadResponseAsync(
        HttpResponseMessage response,
        CancellationToken cancellationToken)
    {
        response.EnsureSuccessStatusCode();
        return await response.Content.ReadFromJsonAsync<Project>(cancellationToken)
            ?? throw new InvalidOperationException("Die API hat keine Projektdaten geliefert.");
    }

    private static async Task<Customer> ReadCustomerResponseAsync(
        HttpResponseMessage response,
        CancellationToken cancellationToken)
    {
        response.EnsureSuccessStatusCode();
        return await response.Content.ReadFromJsonAsync<Customer>(cancellationToken)
            ?? throw new InvalidOperationException("Die API hat keine Kundendaten geliefert.");
    }
}