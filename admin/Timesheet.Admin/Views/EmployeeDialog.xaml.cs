using System.Windows;
using Timesheet.Admin.Models;
using Timesheet.Admin.ViewModels;

namespace Timesheet.Admin.Views;

public partial class EmployeeDialog : Window
{
    private readonly EmployeeDialogViewModel viewModel;

    public EmployeeDialog(Employee? employee)
    {
        InitializeComponent();
        viewModel = new EmployeeDialogViewModel(employee);
        DataContext = viewModel;
        Title = employee is null ? "Benutzer anlegen" : "Benutzer bearbeiten";
    }

    public EmployeeDraft? Result { get; private set; }

    private void Save_Click(object sender, RoutedEventArgs e)
    {
        var draft = viewModel.ToDraft();
        if (string.IsNullOrWhiteSpace(draft.Surname) || string.IsNullOrWhiteSpace(draft.Lastname))
        {
            ValidationMessage.Text = "Vorname und Nachname sind erforderlich.";
            return;
        }

        if (draft.Surname.Length > 100 || draft.Lastname.Length > 100)
        {
            ValidationMessage.Text = "Vorname und Nachname dürfen höchstens 100 Zeichen enthalten.";
            return;
        }

        Result = draft;
        DialogResult = true;
    }
}