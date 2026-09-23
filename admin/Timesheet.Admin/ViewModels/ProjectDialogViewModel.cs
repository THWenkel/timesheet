using System.Collections.ObjectModel;
using CommunityToolkit.Mvvm.ComponentModel;
using Timesheet.Admin.Models;

namespace Timesheet.Admin.ViewModels;

public sealed partial class EmployeeAssignment(Employee employee, bool isAssigned)
    : ObservableObject
{
    public int Id { get; } = employee.Id;
    public string DisplayName { get; } = employee.DisplayName;

    [ObservableProperty]
    private bool isAssigned = isAssigned;
}

public sealed record SelectionOption(string Value, string Label);

public partial class ProjectDialogViewModel : ObservableObject
{
    [ObservableProperty] private string name;
    [ObservableProperty] private string description;
    [ObservableProperty] private string customerName;
    [ObservableProperty] private string purchaseNumber;
    [ObservableProperty] private string unloadingPoint;
    [ObservableProperty] private string consumingPlant;
    [ObservableProperty] private string contactPerson;
    [ObservableProperty] private string contactPhone;
    [ObservableProperty] private string contactEmail;
    [ObservableProperty] private decimal hourlyRate;
    [ObservableProperty] private decimal dailyRate;
    [ObservableProperty] private decimal budgetAmount;
    [ObservableProperty] private string budgetUnit;
    [ObservableProperty] private DateTime startsOn;
    [ObservableProperty] private DateTime endsOn;
    [ObservableProperty] private string status;

    public ProjectDialogViewModel(
        Project? project,
        IReadOnlyList<Employee> employees,
        IReadOnlyList<Customer> customers)
    {
        Name = project?.Name ?? string.Empty;
        Description = project?.Description ?? string.Empty;
        CustomerName = project?.CustomerName ?? string.Empty;
        PurchaseNumber = project?.PurchaseNumber ?? string.Empty;
        UnloadingPoint = project?.UnloadingPoint ?? string.Empty;
        ConsumingPlant = project?.ConsumingPlant ?? string.Empty;
        ContactPerson = project?.ContactPerson ?? string.Empty;
        ContactPhone = project?.ContactPhone ?? string.Empty;
        ContactEmail = project?.ContactEmail ?? string.Empty;
        HourlyRate = project?.HourlyRate ?? 0;
        DailyRate = project?.DailyRate ?? 0;
        BudgetAmount = project?.BudgetAmount ?? 1;
        BudgetUnit = project?.BudgetUnit ?? "hours";
        StartsOn = project is null ? DateTime.Today : project.StartsOn.ToDateTime(TimeOnly.MinValue);
        EndsOn = project is null ? DateTime.Today.AddMonths(1) : project.EndsOn.ToDateTime(TimeOnly.MinValue);
        Status = project?.Status ?? "active";
        CustomerNames = new ObservableCollection<string>(customers.Select(customer => customer.Name));
        Assignments = new ObservableCollection<EmployeeAssignment>(
            employees.Where(employee => employee.IsActive).Select(
                employee => new EmployeeAssignment(
                    employee,
                    project?.EmployeeIds.Contains(employee.Id) == true)));
    }

    public ObservableCollection<string> CustomerNames { get; }
    public ObservableCollection<EmployeeAssignment> Assignments { get; }
    public IReadOnlyList<SelectionOption> BudgetUnits { get; } =
        [new("hours", "Stunden"), new("person_days", "Personentage")];
    public IReadOnlyList<SelectionOption> Statuses { get; } =
        [new("active", "Aktiv"), new("paused", "Pausiert"), new("completed", "Abgeschlossen")];

    public ProjectDraft ToDraft() => new(
        Name.Trim(),
        Description.Trim(),
        CustomerName.Trim(),
        PurchaseNumber.Trim(),
        UnloadingPoint.Trim(),
        ConsumingPlant.Trim(),
        ContactPerson.Trim(),
        ContactPhone.Trim(),
        ContactEmail.Trim(),
        HourlyRate,
        DailyRate,
        BudgetAmount,
        BudgetUnit,
        DateOnly.FromDateTime(StartsOn),
        DateOnly.FromDateTime(EndsOn),
        Status,
        Assignments.Where(assignment => assignment.IsAssigned)
            .Select(assignment => assignment.Id)
            .ToArray());
}