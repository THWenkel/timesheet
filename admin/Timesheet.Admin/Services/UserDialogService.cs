using System.Windows;
using System.Windows.Controls;
using Microsoft.Win32;
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
    bool ConfirmPasswordReset(Employee employee);
    bool ConfirmEmployeeDeletion(Employee employee);
    void ShowTemporaryPassword(TemporaryPassword password);
    string? PickFolder(string? initialDirectory, string? title = null);
    IReadOnlyList<string>? PickFiles(string? initialDirectory);
    bool ConfirmRestore(string source, string details);
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

    public bool ConfirmEmployeeDeletion(Employee employee)
    {
        var result = MessageBox.Show(
            $"Soll {employee.Surname} {employee.Lastname} ENDGÜLTIG gelöscht werden?{Environment.NewLine}{Environment.NewLine}" +
            "Das kann nicht rückgängig gemacht werden. Löschen geht nur, wenn der Benutzer keine " +
            "Zeiteinträge hat. Projektzuordnungen werden mit gelöscht. " +
            "Wenn der Benutzer nur nicht mehr arbeiten soll, wähle stattdessen „Deaktivieren“.",
            "Benutzer löschen",
            MessageBoxButton.YesNo,
            MessageBoxImage.Warning,
            MessageBoxResult.No);
        return result == MessageBoxResult.Yes;
    }

    public bool ConfirmPasswordReset(Employee employee)
    {
        var result = MessageBox.Show(
            $"Für {employee.Surname} {employee.Lastname} wird ein Einmalpasswort gesetzt. " +
            "Das bisherige Passwort und alle laufenden Anmeldungen werden ungültig. " +
            "Der Benutzer muss beim nächsten Login ein neues Passwort wählen.",
            "Einmalpasswort setzen",
            MessageBoxButton.YesNo,
            MessageBoxImage.Warning,
            MessageBoxResult.No);
        return result == MessageBoxResult.Yes;
    }

    public void ShowTemporaryPassword(TemporaryPassword password)
    {
        Clipboard.SetText(password.Password);
        MessageBox.Show(
            $"Benutzername: {password.Username}{Environment.NewLine}" +
            $"Einmalpasswort: {password.Password}{Environment.NewLine}{Environment.NewLine}" +
            "Das Passwort wurde in die Zwischenablage kopiert und wird nur jetzt angezeigt. " +
            "Bitte dem Benutzer auf sicherem Weg mitteilen.",
            "Einmalpasswort",
            MessageBoxButton.OK,
            MessageBoxImage.Information);
    }

    public string? PickFolder(string? initialDirectory, string? title = null)
    {
        var dialog = new OpenFolderDialog
        {
            Title = title ?? "Ordner für die Sicherung wählen",
            Multiselect = false,
        };
        if (!string.IsNullOrWhiteSpace(initialDirectory) && System.IO.Directory.Exists(initialDirectory))
        {
            dialog.InitialDirectory = initialDirectory;
        }

        return dialog.ShowDialog(Application.Current.Windows.OfType<Window>().FirstOrDefault(w => w.IsActive))
            == true ? dialog.FolderName : null;
    }

    public IReadOnlyList<string>? PickFiles(string? initialDirectory)
    {
        var dialog = new OpenFileDialog
        {
            Title = "Sicherungsdateien für die Wiederherstellung wählen",
            Filter = "Sicherungsdateien (*.csv;*.json)|*.csv;*.json",
            Multiselect = true,
        };
        if (!string.IsNullOrWhiteSpace(initialDirectory) && System.IO.Directory.Exists(initialDirectory))
        {
            dialog.InitialDirectory = initialDirectory;
        }

        return dialog.ShowDialog(Application.Current.Windows.OfType<Window>().FirstOrDefault(w => w.IsActive))
            == true ? dialog.FileNames : null;
    }

    // Two steps: a yes/no warning listing what changes, then typing a confirmation word.
    public bool ConfirmRestore(string source, string details)
    {
        var first = MessageBox.Show(
            $"Sind Sie sich wirklich sicher!?{Environment.NewLine}{Environment.NewLine}" +
            $"Quelle: {source}{Environment.NewLine}{Environment.NewLine}{details}{Environment.NewLine}{Environment.NewLine}" +
            "Vorhandene Datensätze werden mit dem Stand der Sicherung überschrieben. " +
            "Es werden keine Datensätze gelöscht.",
            "Wiederherstellung bestätigen",
            MessageBoxButton.YesNo,
            MessageBoxImage.Warning,
            MessageBoxResult.No);
        if (first != MessageBoxResult.Yes)
        {
            return false;
        }

        const string word = "WIEDERHERSTELLEN";
        var input = new TextBox { Margin = new Thickness(0, 8, 0, 12) };
        var ok = new Button { Content = "Wiederherstellen", IsDefault = true, IsEnabled = false };
        var cancel = new Button { Content = "Abbrechen", IsCancel = true };
        var window = new Window
        {
            Title = "Wiederherstellung endgültig bestätigen",
            Width = 420,
            SizeToContent = SizeToContent.Height,
            WindowStartupLocation = WindowStartupLocation.CenterOwner,
            Owner = Application.Current.Windows.OfType<Window>().FirstOrDefault(w => w.IsActive),
            ResizeMode = ResizeMode.NoResize,
            Content = new StackPanel
            {
                Margin = new Thickness(20),
                Children =
                {
                    new TextBlock
                    {
                        Text = $"Zur Bestätigung bitte {word} eintippen:",
                        TextWrapping = TextWrapping.Wrap,
                    },
                    input,
                    new StackPanel
                    {
                        Orientation = Orientation.Horizontal,
                        HorizontalAlignment = HorizontalAlignment.Right,
                        Children = { ok, cancel },
                    },
                },
            },
        };
        input.TextChanged += (_, _) => ok.IsEnabled = input.Text.Trim() == word;
        ok.Click += (_, _) => window.DialogResult = true;
        return window.ShowDialog() == true;
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

public interface IBackupWindowService
{
    void Show();
}

public sealed class BackupWindowService(
    IBackupApiClient backupApiClient,
    IUserDialogService dialogService,
    ISettingsService settingsService) : IBackupWindowService
{
    public void Show()
    {
        var viewModel = new BackupViewModel(backupApiClient, dialogService, settingsService);
        var window = new BackupWindow
        {
            Owner = Application.Current.MainWindow,
            DataContext = viewModel,
        };
        viewModel.LoadCommand.Execute(null);
        window.ShowDialog();
    }
}
