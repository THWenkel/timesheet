using System.Windows;
using Timesheet.Admin.Services;

namespace Timesheet.Admin.Views;

/// <summary>
/// Login before anything else. After an administrator reset the password, the same window
/// asks for a new one. Only accounts with the administrator flag may continue.
/// </summary>
public partial class LoginWindow : Window
{
    private const int MinPasswordLength = 10;

    private readonly IAuthApiClient authApiClient;
    private string? usedPassword;

    public LoginWindow(IAuthApiClient authApiClient)
    {
        InitializeComponent();
        this.authApiClient = authApiClient;
        Loaded += (_, _) => UsernameBox.Focus();
    }

    private async void Submit_Click(object sender, RoutedEventArgs e)
    {
        ErrorText.Text = string.Empty;
        SubmitButton.IsEnabled = false;
        try
        {
            if (ChangePanel.Visibility == Visibility.Visible)
            {
                await ChangePasswordAsync();
            }
            else
            {
                await LoginAsync();
            }
        }
        finally
        {
            SubmitButton.IsEnabled = true;
        }
    }

    private async Task LoginAsync()
    {
        var username = UsernameBox.Text.Trim();
        var password = PasswordBox.Password;
        if (username.Length == 0 || password.Length == 0)
        {
            ErrorText.Text = "Bitte Benutzername und Passwort eingeben.";
            return;
        }

        var result = await authApiClient.LoginAsync(username, password);
        PasswordBox.Clear();
        if (result.User is null)
        {
            ErrorText.Text = result.Error ?? "Anmeldung fehlgeschlagen.";
            return;
        }

        if (!result.User.IsAdmin)
        {
            ErrorText.Text = "Dieser Benutzer ist kein Administrator.";
            return;
        }

        if (result.User.MustChangePassword)
        {
            usedPassword = password;
            LoginPanel.Visibility = Visibility.Collapsed;
            ChangePanel.Visibility = Visibility.Visible;
            Subtitle.Text = "Das Passwort wurde zurückgesetzt. Bitte ein eigenes Passwort wählen.";
            SubmitButton.Content = "Passwort ändern";
            NewPasswordBox.Focus();
            return;
        }

        DialogResult = true;
    }

    private async Task ChangePasswordAsync()
    {
        var next = NewPasswordBox.Password;
        if (next.Length < MinPasswordLength)
        {
            ErrorText.Text = $"Das Passwort muss mindestens {MinPasswordLength} Zeichen lang sein.";
            return;
        }

        if (next != RepeatPasswordBox.Password)
        {
            ErrorText.Text = "Die Passwörter stimmen nicht überein.";
            return;
        }

        var result = await authApiClient.ChangePasswordAsync(usedPassword ?? string.Empty, next);
        if (result.User is null)
        {
            ErrorText.Text = result.Error ?? "Das Passwort konnte nicht geändert werden.";
            return;
        }

        usedPassword = null;
        DialogResult = true;
    }
}
