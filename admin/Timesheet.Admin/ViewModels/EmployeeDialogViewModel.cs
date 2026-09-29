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

    [ObservableProperty]
    private string username;

    [ObservableProperty]
    private bool isAdmin;

    public EmployeeDialogViewModel(Employee? employee)
    {
        Surname = employee?.Surname ?? string.Empty;
        Lastname = employee?.Lastname ?? string.Empty;
        IsActive = employee?.IsActive ?? true;
        Username = employee?.Username ?? string.Empty;
        IsAdmin = employee?.IsAdmin ?? false;
    }

    public EmployeeDraft ToDraft() => new(Surname.Trim(), Lastname.Trim(), IsActive, Username.Trim(), IsAdmin);
}