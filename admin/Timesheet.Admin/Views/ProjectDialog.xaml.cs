using System.Windows;
using Timesheet.Admin.Models;
using Timesheet.Admin.ViewModels;

namespace Timesheet.Admin.Views;

public partial class ProjectDialog : Window
{
    private readonly ProjectDialogViewModel viewModel;

    public ProjectDialog(
        Project? project,
        IReadOnlyList<Employee> employees,
        IReadOnlyList<Customer> customers)
    {
        InitializeComponent();
        viewModel = new ProjectDialogViewModel(project, employees, customers);
        DataContext = viewModel;
        Title = project is null ? "Projekt anlegen" : "Projekt bearbeiten";
    }

    public ProjectDraft? Result { get; private set; }

    private void Save_Click(object sender, RoutedEventArgs e)
    {
        var draft = viewModel.ToDraft();
        if (string.IsNullOrWhiteSpace(draft.Name) || string.IsNullOrWhiteSpace(draft.CustomerName))
        {
            ValidationMessage.Text = "Projektname und Kunde sind erforderlich.";
            return;
        }
        if (draft.BudgetAmount <= 0)
        {
            ValidationMessage.Text = "Das Budget muss größer als null sein.";
            return;
        }
        if (draft.HourlyRate < 0 || draft.DailyRate < 0)
        {
            ValidationMessage.Text = "Preis je Stunde und Tagessatz dürfen nicht negativ sein.";
            return;
        }
        if (draft.EndsOn < draft.StartsOn)
        {
            ValidationMessage.Text = "Das Laufzeitende darf nicht vor dem Beginn liegen.";
            return;
        }
        if (draft.PurchaseNumber.Length > 100
            || draft.UnloadingPoint.Length > 200
            || draft.ConsumingPlant.Length > 200
            || draft.ContactPerson.Length > 200
            || draft.ContactPhone.Length > 50
            || draft.ContactEmail.Length > 254)
        {
            ValidationMessage.Text = "Mindestens ein Projektfeld überschreitet die zulässige Länge.";
            return;
        }

        Result = draft;
        DialogResult = true;
    }
}