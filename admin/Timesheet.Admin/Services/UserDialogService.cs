using System.Windows;
using Timesheet.Admin.Models;
using Timesheet.Admin.ViewModels;
using Timesheet.Admin.Views;

namespace Timesheet.Admin.Services;

public interface IUserDialogService
{
    EmployeeDraft? EditEmployee(Employee? employee);
    ProjectDraft? EditProject(
        Project? project,
        IReadOnlyList<Employee> employees,
        IReadOnlyList<Customer> customers);
    CustomerDraft? EditCustomer(
        Customer? customer,
        IReadOnlyList<CountryCode2> countryCodes);
    bool ConfirmDeactivation(Employee employee);
    bool ConfirmCustomerDeactivation(Customer customer);
}

public sealed class UserDialogService : IUserDialogService
{
    public EmployeeDraft? EditEmployee(Employee? employee)
    {
        var dialog = new EmployeeDialog(employee)
        {
            Owner = Application.Current.MainWindow,
        };
        return dialog.ShowDialog() == true ? dialog.Result : null;
    }

    public ProjectDraft? EditProject(
        Project? project,
        IReadOnlyList<Employee> employees,
        IReadOnlyList<Customer> customers)
    {
        var dialog = new ProjectDialog(project, employees, customers)
        {
            Owner = Application.Current.Windows.OfType<Window>().FirstOrDefault(window => window.IsActive)
                ?? Application.Current.MainWindow,
        };
        return dialog.ShowDialog() == true ? dialog.Result : null;
    }

    public CustomerDraft? EditCustomer(
        Customer? customer,
        IReadOnlyList<CountryCode2> countryCodes)
    {
        var dialog = new CustomerDialog(customer, countryCodes)
        {
            Owner = Application.Current.Windows.OfType<Window>().FirstOrDefault(window => window.IsActive)
                ?? Application.Current.MainWindow,
        };
        return dialog.ShowDialog() == true ? dialog.Result : null;
    }

    public bool ConfirmDeactivation(Employee employee)
    {
        var result = MessageBox.Show(
            $"Soll {employee.Surname} {employee.Lastname} wirklich deaktiviert werden?",
            "Benutzer deaktivieren",
            MessageBoxButton.YesNo,
            MessageBoxImage.Warning,
            MessageBoxResult.No);
        return result == MessageBoxResult.Yes;
    }

    public bool ConfirmCustomerDeactivation(Customer customer)
    {
        var result = MessageBox.Show(
            $"Soll der Kunde {customer.Name} wirklich deaktiviert werden?",
            "Kunde deaktivieren",
            MessageBoxButton.YesNo,
            MessageBoxImage.Warning,
            MessageBoxResult.No);
        return result == MessageBoxResult.Yes;
    }
}

public interface IProjectWindowService
{
    void Show();
}

public sealed class ProjectWindowService(
    IProjectApiClient projectApiClient,
    IEmployeeApiClient employeeApiClient,
    IUserDialogService dialogService) : IProjectWindowService
{
    public void Show()
    {
        var viewModel = new ProjectManagementViewModel(
            projectApiClient, employeeApiClient, dialogService);
        var window = new ProjectManagementWindow
        {
            Owner = Application.Current.MainWindow,
            DataContext = viewModel,
        };
        viewModel.LoadCommand.Execute(null);
        window.ShowDialog();
    }
}

public interface ICustomerWindowService
{
    void Show();
}

public sealed class CustomerWindowService(
    IProjectApiClient projectApiClient,
    IUserDialogService dialogService) : ICustomerWindowService
{
    public void Show()
    {
        var viewModel = new CustomerManagementViewModel(projectApiClient, dialogService);
        var window = new CustomerManagementWindow
        {
            Owner = Application.Current.MainWindow,
            DataContext = viewModel,
        };
        viewModel.LoadCommand.Execute(null);
        window.ShowDialog();
    }
}