using System.Collections.ObjectModel;
using System.Net.Http;
using CommunityToolkit.Mvvm.ComponentModel;
using CommunityToolkit.Mvvm.Input;
using Timesheet.Admin.Models;
using Timesheet.Admin.Services;

namespace Timesheet.Admin.ViewModels;

public partial class MainWindowViewModel(
    IEmployeeApiClient employeeApiClient,
    IProjectApiClient projectApiClient,
    IUserDialogService dialogService,
    IProjectWindowService projectWindowService,
    ICustomerWindowService customerWindowService,
    IBackupWindowService backupWindowService) : ObservableObject
{
    [ObservableProperty]
    private ObservableCollection<Employee> employees = [];

    [ObservableProperty]
    private ObservableCollection<Project> employeeProjects = [];

    [ObservableProperty]
    [NotifyCanExecuteChangedFor(nameof(EditCommand))]
    [NotifyCanExecuteChangedFor(nameof(DeactivateCommand))]
    [NotifyCanExecuteChangedFor(nameof(ResetPasswordCommand))]
    [NotifyCanExecuteChangedFor(nameof(DeleteCommand))]
    private Employee? selectedEmployee;

    partial void OnSelectedEmployeeChanged(Employee? value)
    {
        if (value is null)
        {
            EmployeeProjects = [];
            return;
        }
        LoadEmployeeProjectsCommand.Execute(null);
    }

    [ObservableProperty]
    [NotifyCanExecuteChangedFor(nameof(AddCommand))]
    [NotifyCanExecuteChangedFor(nameof(EditCommand))]
    [NotifyCanExecuteChangedFor(nameof(DeactivateCommand))]
    [NotifyCanExecuteChangedFor(nameof(LoadCommand))]
    [NotifyCanExecuteChangedFor(nameof(OpenProjectsCommand))]
    [NotifyCanExecuteChangedFor(nameof(OpenCustomersCommand))]
    [NotifyCanExecuteChangedFor(nameof(OpenBackupCommand))]
    [NotifyCanExecuteChangedFor(nameof(ResetPasswordCommand))]
    [NotifyCanExecuteChangedFor(nameof(DeleteCommand))]
    private bool isBusy;

    [ObservableProperty]
    private string? errorMessage;

    [ObservableProperty]
    private string statusText = "Bereit";

    [RelayCommand(CanExecute = nameof(IsNotBusy))]
    private async Task LoadAsync()
    {
        await RunAsync(async () =>
        {
            var employees = await employeeApiClient.GetAllAsync();
            Employees = new ObservableCollection<Employee>(employees);
            StatusText = $"{Employees.Count} Benutzer geladen";
        });
    }

    [RelayCommand(CanExecute = nameof(IsNotBusy))]
    private async Task AddAsync()
    {
        var draft = dialogService.EditEmployee(null);
        if (draft is null)
        {
            return;
        }

        await RunAsync(async () =>
        {
            await employeeApiClient.CreateAsync(draft);
            await RefreshAsync();
            StatusText = "Benutzer wurde angelegt";
        });
    }

    [RelayCommand(CanExecute = nameof(CanModifyEmployee))]
    private async Task EditAsync()
    {
        var employee = SelectedEmployee;
        if (employee is null)
        {
            return;
        }

        var draft = dialogService.EditEmployee(employee);
        if (draft is null)
        {
            return;
        }

        await RunAsync(async () =>
        {
            await employeeApiClient.UpdateAsync(employee.Id, draft);
            await RefreshAsync(employee.Id);
            StatusText = "Benutzer wurde aktualisiert";
        });
    }

    [RelayCommand(CanExecute = nameof(CanDeactivateEmployee))]
    private async Task DeactivateAsync()
    {
        var employee = SelectedEmployee;
        if (employee is null || !dialogService.ConfirmDeactivation(employee))
        {
            return;
        }

        var draft = new EmployeeDraft(employee.Surname, employee.Lastname, false);
        await RunAsync(async () =>
        {
            await employeeApiClient.UpdateAsync(employee.Id, draft);
            await RefreshAsync(employee.Id);
            StatusText = "Benutzer wurde deaktiviert";
        });
    }

    [RelayCommand(CanExecute = nameof(CanModifyEmployee))]
    private async Task DeleteAsync()
    {
        var employee = SelectedEmployee;
        if (employee is null || !dialogService.ConfirmEmployeeDeletion(employee))
        {
            return;
        }

        await RunAsync(async () =>
        {
            await employeeApiClient.DeleteAsync(employee.Id);
            await RefreshAsync();
            StatusText = "Benutzer wurde gelöscht";
        });
    }

    [RelayCommand(CanExecute = nameof(CanModifyEmployee))]
    private async Task ResetPasswordAsync()
    {
        var employee = SelectedEmployee;
        if (employee is null || !dialogService.ConfirmPasswordReset(employee))
        {
            return;
        }

        await RunAsync(async () =>
        {
            var result = await employeeApiClient.ResetPasswordAsync(employee.Id);
            await RefreshAsync(employee.Id);
            dialogService.ShowTemporaryPassword(result);
            StatusText = "Einmalpasswort wurde gesetzt";
        });
    }

    [RelayCommand(CanExecute = nameof(IsNotBusy))]
    private async Task OpenProjectsAsync()
    {
        projectWindowService.Show();
        await LoadEmployeeProjectsAsync();
    }

    [RelayCommand(CanExecute = nameof(IsNotBusy))]
    private void OpenCustomers() => customerWindowService.Show();

    [RelayCommand(CanExecute = nameof(IsNotBusy))]
    private void OpenBackup() => backupWindowService.Show();

    [RelayCommand]
    private async Task LoadEmployeeProjectsAsync()
    {
        var employee = SelectedEmployee;
        if (employee is null)
        {
            EmployeeProjects = [];
            return;
        }

        try
        {
            EmployeeProjects = new ObservableCollection<Project>(
                await projectApiClient.GetForEmployeeAsync(employee.Id));
        }
        catch (Exception exception)
        {
            ErrorMessage = $"Projekte konnten nicht geladen werden: {exception.Message}";
        }
    }

    private bool IsNotBusy() => !IsBusy;

    private bool CanModifyEmployee() => SelectedEmployee is not null && !IsBusy;

    private bool CanDeactivateEmployee() => SelectedEmployee?.IsActive == true && !IsBusy;

    private async Task RefreshAsync(int? selectedId = null)
    {
        var employees = await employeeApiClient.GetAllAsync();
        Employees = new ObservableCollection<Employee>(employees);
        SelectedEmployee = selectedId is null
            ? null
            : Employees.FirstOrDefault(employee => employee.Id == selectedId);
    }

    private async Task RunAsync(Func<Task> operation)
    {
        IsBusy = true;
        ErrorMessage = null;
        StatusText = "Wird verarbeitet …";
        try
        {
            await operation();
        }
        catch (HttpRequestException exception)
        {
            ErrorMessage = $"Die Timesheet-API ist nicht erreichbar: {exception.Message}";
            StatusText = "Fehler";
        }
        catch (Exception exception)
        {
            ErrorMessage = exception.Message;
            StatusText = "Fehler";
        }
        finally
        {
            IsBusy = false;
        }
    }
}