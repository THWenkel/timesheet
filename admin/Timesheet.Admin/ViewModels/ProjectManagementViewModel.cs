using System.Collections.ObjectModel;
using System.Net.Http;
using CommunityToolkit.Mvvm.ComponentModel;
using CommunityToolkit.Mvvm.Input;
using Timesheet.Admin.Models;
using Timesheet.Admin.Services;

namespace Timesheet.Admin.ViewModels;

public partial class ProjectManagementViewModel(
    IProjectApiClient projectApiClient,
    IEmployeeApiClient employeeApiClient,
    IUserDialogService dialogService) : ObservableObject
{
    [ObservableProperty] private ObservableCollection<Project> projects = [];
    [ObservableProperty] private Project? selectedProject;
    [ObservableProperty] private bool isBusy;
    [ObservableProperty] private string? errorMessage;
    [ObservableProperty] private string statusText = "Bereit";

    private IReadOnlyList<Employee> employees = [];
    private IReadOnlyList<Customer> customers = [];

    partial void OnSelectedProjectChanged(Project? value) => EditCommand.NotifyCanExecuteChanged();
    partial void OnIsBusyChanged(bool value)
    {
        AddCommand.NotifyCanExecuteChanged();
        EditCommand.NotifyCanExecuteChanged();
        LoadCommand.NotifyCanExecuteChanged();
    }

    [RelayCommand(CanExecute = nameof(IsNotBusy))]
    private async Task LoadAsync() => await RunAsync(() => RefreshAsync());

    [RelayCommand(CanExecute = nameof(IsNotBusy))]
    private async Task AddAsync()
    {
        var draft = dialogService.EditProject(null, employees, customers);
        if (draft is null) return;
        await RunAsync(async () =>
        {
            await projectApiClient.CreateAsync(draft);
            await RefreshAsync();
            StatusText = "Projekt wurde angelegt";
        });
    }

    [RelayCommand(CanExecute = nameof(CanEdit))]
    private async Task EditAsync()
    {
        var project = SelectedProject;
        if (project is null) return;
        var draft = dialogService.EditProject(project, employees, customers);
        if (draft is null) return;
        await RunAsync(async () =>
        {
            await projectApiClient.UpdateAsync(project.Id, draft);
            await RefreshAsync(project.Id);
            StatusText = "Projekt wurde aktualisiert";
        });
    }

    private bool IsNotBusy() => !IsBusy;
    private bool CanEdit() => SelectedProject is not null && !IsBusy;

    private async Task RefreshAsync(int? selectedId = null)
    {
        var projectTask = projectApiClient.GetAllAsync();
        var employeeTask = employeeApiClient.GetAllAsync();
        var customerTask = projectApiClient.GetCustomersAsync();
        await Task.WhenAll(projectTask, employeeTask, customerTask);
        employees = await employeeTask;
        customers = await customerTask;
        Projects = new ObservableCollection<Project>(await projectTask);
        SelectedProject = Projects.FirstOrDefault(project => project.Id == selectedId);
        StatusText = $"{Projects.Count} Projekte geladen";
    }

    private async Task RunAsync(Func<Task> operation)
    {
        IsBusy = true;
        ErrorMessage = null;
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