using System.Windows;
using Timesheet.Admin.Models;
using Timesheet.Admin.ViewModels;

namespace Timesheet.Admin.Views;

public partial class CustomerDialog : Window
{
    private readonly CustomerDialogViewModel viewModel;

    public CustomerDialog(
        Customer? customer,
        IReadOnlyList<CountryCode2> countryCodes)
    {
        InitializeComponent();
        viewModel = new CustomerDialogViewModel(customer, countryCodes);
        DataContext = viewModel;
        Title = customer is null ? "Kunde anlegen" : "Kunde bearbeiten";
    }

    public CustomerDraft? Result { get; private set; }

    private void Save_Click(object sender, RoutedEventArgs e)
    {
        var draft = viewModel.ToDraft();
        if (string.IsNullOrWhiteSpace(draft.Name))
        {
            ValidationMessage.Text = "Der Kundenname ist erforderlich.";
            return;
        }
        if (!viewModel.CountryCodes.Any(
            item => string.Equals(
                item.CountryCode,
                draft.Country,
                StringComparison.OrdinalIgnoreCase)))
        {
            ValidationMessage.Text = "Bitte einen gültigen zweistelligen Ländercode auswählen.";
            return;
        }
        if (draft.Name.Length > 200 || draft.Notes.Length > 2000)
        {
            ValidationMessage.Text = "Name oder Notizen überschreiten die zulässige Länge.";
            return;
        }
        if (draft.Street1.Length > 200 || draft.Street2.Length > 200
            || draft.PostalCode.Length > 20 || draft.City.Length > 100
            || draft.Country.Length > 100 || draft.SupplierNumber.Length > 100
            || draft.ContactPerson.Length > 200
            || draft.ContactPhone.Length > 50 || draft.ContactEmail.Length > 254)
        {
            ValidationMessage.Text = "Mindestens ein Feld überschreitet die zulässige Länge.";
            return;
        }

        Result = draft;
        DialogResult = true;
    }
}