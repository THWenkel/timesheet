using CommunityToolkit.Mvvm.ComponentModel;
using Timesheet.Admin.Models;

namespace Timesheet.Admin.ViewModels;

public partial class EmployeeDialogViewModel : ObservableObject
{
    [ObservableProperty]
    private string surname;

    [ObservableProperty]
    private string lastname;

    [ObservableProperty]
    private bool isActive;

    public EmployeeDialogViewModel(Employee? employee)
    {
        Surname = employee?.Surname ?? string.Empty;
        Lastname = employee?.Lastname ?? string.Empty;
        IsActive = employee?.IsActive ?? true;
    }

    public EmployeeDraft ToDraft() => new(Surname.Trim(), Lastname.Trim(), IsActive);
}