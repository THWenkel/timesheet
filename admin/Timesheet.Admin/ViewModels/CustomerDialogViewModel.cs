using System.ComponentModel;
using CommunityToolkit.Mvvm.ComponentModel;
using System.Windows.Data;
using Timesheet.Admin.Models;

namespace Timesheet.Admin.ViewModels;

public partial class CustomerDialogViewModel : ObservableObject
{
    private readonly ICollectionView countryCodesView;

    [ObservableProperty] private string name;
    [ObservableProperty] private string notes;
    [ObservableProperty] private string street1;
    [ObservableProperty] private string street2;
    [ObservableProperty] private string postalCode;
    [ObservableProperty] private string city;
    [ObservableProperty] private string country;
    [ObservableProperty] private string searchText;
    [ObservableProperty] private string supplierNumber;
    [ObservableProperty] private string contactPerson;
    [ObservableProperty] private string contactPhone;
    [ObservableProperty] private string contactEmail;
    [ObservableProperty] private bool isActive;

    public CustomerDialogViewModel(
        Customer? customer,
        IReadOnlyList<CountryCode2> countryCodes)
    {
        CountryCodes = countryCodes
            .OrderBy(item => item.CountryCode, StringComparer.OrdinalIgnoreCase)
            .ToArray();
        countryCodesView = CollectionViewSource.GetDefaultView(CountryCodes);
        countryCodesView.Filter = MatchesCountryFilter;
        Name = customer?.Name ?? string.Empty;
        Notes = customer?.Notes ?? string.Empty;
        Street1 = customer?.Street1 ?? string.Empty;
        Street2 = customer?.Street2 ?? string.Empty;
        PostalCode = customer?.PostalCode ?? string.Empty;
        City = customer?.City ?? string.Empty;
        Country = customer?.Country ?? string.Empty;
        SearchText = GetCountryDisplayName(Country);
        SupplierNumber = customer?.SupplierNumber ?? string.Empty;
        ContactPerson = customer?.ContactPerson ?? string.Empty;
        ContactPhone = customer?.ContactPhone ?? string.Empty;
        ContactEmail = customer?.ContactEmail ?? string.Empty;
        IsActive = customer?.IsActive ?? true;
    }

    public IReadOnlyList<CountryCode2> CountryCodes { get; }
    public ICollectionView FilteredCountryCodes => countryCodesView;

    partial void OnCountryChanged(string value) => SearchText = GetCountryDisplayName(value);

    partial void OnSearchTextChanged(string value) => countryCodesView.Refresh();

    private bool MatchesCountryFilter(object item) =>
        item is CountryCode2 countryCode
        && (string.IsNullOrWhiteSpace(SearchText)
            || string.Equals(SearchText, GetCountryDisplayName(Country), StringComparison.Ordinal)
            || countryCode.CountryCode.Contains(SearchText.Trim(), StringComparison.OrdinalIgnoreCase)
            || countryCode.CountryName.Contains(SearchText.Trim(), StringComparison.OrdinalIgnoreCase));

    private string GetCountryDisplayName(string countryCode) =>
        CountryCodes.FirstOrDefault(
            item => string.Equals(
                item.CountryCode,
                countryCode,
                StringComparison.OrdinalIgnoreCase))?.DisplayName
        ?? countryCode;

    public CustomerDraft ToDraft() => new(
        Name.Trim(),
        Notes.Trim(),
        Street1.Trim(),
        Street2.Trim(),
        PostalCode.Trim(),
        City.Trim(),
        Country.Trim(),
        SupplierNumber.Trim(),
        ContactPerson.Trim(),
        ContactPhone.Trim(),
        ContactEmail.Trim(),
        IsActive);
}