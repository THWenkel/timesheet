using System.Net.Http;
using System.Windows;
using System.Windows.Media;
using Timesheet.Admin.Services;

namespace Timesheet.Admin.Views;

/// <summary>
/// Asks for the address of the API backend and can test it. Shown at the first start, when
/// the configured server cannot be reached, and from the login window ("Server ändern").
/// </summary>
public partial class ServerSettingsWindow : Window
{
    private static readonly Brush ErrorBrush = new SolidColorBrush(Color.FromRgb(0xA1, 0x28, 0x28));
    private static readonly Brush SuccessBrush = new SolidColorBrush(Color.FromRgb(0x17, 0x6B, 0x57));

    public ServerSettingsWindow(string? currentUrl, string? problem, ApiUrlSource source)
    {
        InitializeComponent();
        UrlBox.Text = currentUrl ?? string.Empty;
        ShowStatus(problem, isError: true);
        if (source == ApiUrlSource.Environment)
        {
            HintText.Text = $"Hinweis: Die Umgebungsvariable {ApiEndpoint.EnvironmentVariable} ist gesetzt. "
                + "Sie hat beim nächsten Start Vorrang vor dieser Einstellung.";
        }

        Loaded += (_, _) =>
        {
            UrlBox.Focus();
            UrlBox.SelectAll();
        };
    }

    /// <summary>The validated address (with trailing slash) after "Speichern und verbinden".</summary>
    public Uri? ServerUri { get; private set; }

    private async void Test_Click(object sender, RoutedEventArgs e)
    {
        if (!TryReadUri(out var uri))
        {
            return;
        }

        TestButton.IsEnabled = false;
        SaveButton.IsEnabled = false;
        ShowStatus("Verbindung wird geprüft ...", isError: false);
        try
        {
            using var client = new HttpClient { BaseAddress = uri };
            var problem = await new AuthApiClient(client).CheckConnectionAsync();
            if (problem is not null)
            {
                ShowStatus(problem, isError: true);
            }
            else if (uri.Scheme == Uri.UriSchemeHttp && !uri.IsLoopback)
            {
                ShowStatus(
                    "Verbindung hergestellt. Hinweis: Über http:// funktioniert die Anmeldung nur, "
                    + "wenn der Server COOKIE_SECURE=false hat. Im Produktivbetrieb https:// verwenden.",
                    isError: false);
            }
            else
            {
                ShowStatus("Verbindung hergestellt: Das Timesheet-API antwortet.", isError: false);
            }
        }
        finally
        {
            TestButton.IsEnabled = true;
            SaveButton.IsEnabled = true;
        }
    }

    private void Save_Click(object sender, RoutedEventArgs e)
    {
        if (TryReadUri(out var uri))
        {
            ServerUri = uri;
            DialogResult = true;
        }
    }

    private bool TryReadUri(out Uri uri)
    {
        if (ApiEndpoint.TryNormalize(UrlBox.Text, out uri))
        {
            UrlBox.Text = uri.ToString();
            return true;
        }

        ShowStatus("Bitte eine vollständige Adresse mit http:// oder https:// eingeben.", isError: true);
        return false;
    }

    private void ShowStatus(string? text, bool isError)
    {
        StatusText.Text = text ?? string.Empty;
        StatusText.Foreground = isError ? ErrorBrush : SuccessBrush;
    }
}
