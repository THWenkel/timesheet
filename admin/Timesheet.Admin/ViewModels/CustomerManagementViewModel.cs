using System.Collections.ObjectModel;
using System.Net.Http;
using CommunityToolkit.Mvvm.ComponentModel;
using CommunityToolkit.Mvvm.Input;
using Timesheet.Admin.Models;
using Timesheet.Admin.Services;

namespace Timesheet.Admin.ViewModels;

public partial class CustomerManagementViewModel(
    IProjectApiClient projectApiClient,
    IUserDialogService dialogService) : ObservableObject
{
    [ObservableProperty] private ObservableCollection<Customer> customers = [];
    [ObservableProperty] private Customer? selectedCustomer;
    [ObservableProperty] private bool isBusy;
    [ObservableProperty] private string? errorMessage;
    [ObservableProperty] private string statusText = "Bereit";

    private IReadOnlyList<CountryCode2> countryCodes = [];

    partial void OnSelectedCustomerChanged(Customer? value)
    {
        EditCommand.NotifyCanExecuteChanged();
        DeactivateCommand.NotifyCanExecuteChanged();
    }

    partial void OnIsBusyChanged(bool value)
    {
        AddCommand.NotifyCanExecuteChanged();
        EditCommand.NotifyCanExecuteChanged();
        DeactivateCommand.NotifyCanExecuteChanged();
        LoadCommand.NotifyCanExecuteChanged();
    }

    [RelayCommand(CanExecute = nameof(IsNotBusy))]
    private async Task LoadAsync() => await RunAsync(() => RefreshAsync());

    [RelayCommand(CanExecute = nameof(IsNotBusy))]
    private async Task AddAsync()
    {
        var draft = dialogService.EditCustomer(null, countryCodes);
        if (draft is null) return;
        await RunAsync(async () =>
        {
            await projectApiClient.CreateCustomerAsync(draft);
            await RefreshAsync();
            StatusText = "Kunde wurde angelegt";
        });
    }

    [RelayCommand(CanExecute = nameof(CanEdit))]
    private async Task EditAsync()
    {
        var customer = SelectedCustomer;
        if (customer is null) return;
        var draft = dialogService.EditCustomer(customer, countryCodes);
        if (draft is null) return;
        await RunAsync(async () =>
        {
            await projectApiClient.UpdateCustomerAsync(customer.Id, draft);
            await RefreshAsync(customer.Id);
            StatusText = "Kunde wurde aktualisiert";
        });
    }

    [RelayCommand(CanExecute = nameof(CanDeactivate))]
    private async Task DeactivateAsync()
    {
        var customer = SelectedCustomer;
        if (customer is null || !dialogService.ConfirmCustomerDeactivation(customer)) return;
        var draft = new CustomerDraft(
            customer.Name,
            customer.Notes,
            customer.Street1,
            customer.Street2,
            customer.PostalCode,
            customer.City,
            customer.Country,
            customer.SupplierNumber,
            customer.ContactPerson,
            customer.ContactPhone,
            customer.ContactEmail,
            false);
        await RunAsync(async () =>
        {
            await projectApiClient.UpdateCustomerAsync(customer.Id, draft);
            await RefreshAsync(customer.Id);
            StatusText = "Kunde wurde deaktiviert";
        });
    }

    private bool IsNotBusy() => !IsBusy;
    private bool CanEdit() => SelectedCustomer is not null && !IsBusy;
    private bool CanDeactivate() => SelectedCustomer?.IsActive == true && !IsBusy;

    private async Task RefreshAsync(int? selectedId = null)
    {
        var customersTask = projectApiClient.GetAllCustomersAsync();
        var countryCodesTask = projectApiClient.GetCountryCodesAsync();
        await Task.WhenAll(customersTask, countryCodesTask);
        Customers = new ObservableCollection<Customer>(await customersTask);
        countryCodes = await countryCodesTask;
        SelectedCustomer = Customers.FirstOrDefault(customer => customer.Id == selectedId);
        StatusText = $"{Customers.Count} Kunden geladen";
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