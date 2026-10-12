using System.Net;
using System.Net.Http;
using System.Windows;
using Timesheet.Admin.Services;
using Timesheet.Admin.ViewModels;
using Timesheet.Admin.Views;

namespace Timesheet.Admin;

/// <summary>
/// Interaction logic for App.xaml
/// </summary>
public partial class App : Application
{
	protected override async void OnStartup(StartupEventArgs e)
	{
		base.OnStartup(e);

		// Nothing works without a connection and a login: keep the app alive until both are done.
		ShutdownMode = ShutdownMode.OnExplicitShutdown;
		var settingsService = new SettingsService();
		var httpClient = await ConnectAsync(settingsService);
		if (httpClient is null)
		{
			Shutdown();
			return;
		}

		var employeeApiClient = new EmployeeApiClient(httpClient);
		var projectApiClient = new ProjectApiClient(httpClient);
		var backupApiClient = new BackupApiClient(httpClient);
		var dialogService = new UserDialogService();
		var viewModel = new MainWindowViewModel(
			employeeApiClient,
			projectApiClient,
			dialogService,
			new ProjectWindowService(projectApiClient, employeeApiClient, dialogService),
			new CustomerWindowService(projectApiClient, dialogService),
			new BackupWindowService(backupApiClient, dialogService, settingsService));

		MainWindow = new MainWindow { DataContext = viewModel };
		ShutdownMode = ShutdownMode.OnMainWindowClose;
		MainWindow.Show();
		viewModel.LoadCommand.Execute(null);
	}

	/// <summary>
	/// Finds the API (environment variable, saved setting, appsettings.json), asks for the
	/// address if it is missing or unreachable, and logs in. Null means the user gave up.
	/// </summary>
	private static async Task<HttpClient?> ConnectAsync(ISettingsService settingsService)
	{
		var choice = ApiEndpoint.Resolve(settingsService);
		var url = choice.Url;
		var problem = url is null ? "Es ist noch keine Server-Adresse eingestellt." : null;
		var askForUrl = url is null;

		while (true)
		{
			if (!askForUrl)
			{
				if (ApiEndpoint.TryNormalize(url, out var baseUri))
				{
					// The session is an HttpOnly cookie; the CSRF handler echoes the CSRF cookie in a header.
					var cookies = new CookieContainer();
					var handler = new CsrfHandler(cookies, baseUri)
					{
						InnerHandler = new HttpClientHandler { CookieContainer = cookies, UseCookies = true },
					};
					var httpClient = new HttpClient(handler) { BaseAddress = baseUri };
					var authApiClient = new AuthApiClient(httpClient);

					problem = await authApiClient.CheckConnectionAsync();
					if (problem is null)
					{
						// While AUTH_ENABLED=false on the server (first setup: create the administrator
						// accounts and one-time passwords) no login is needed or possible to enforce.
						if (!await authApiClient.IsAuthEnabledAsync())
						{
							return httpClient;
						}

						var loginWindow = new LoginWindow(authApiClient, baseUri);
						if (loginWindow.ShowDialog() == true)
						{
							return httpClient;
						}

						if (!loginWindow.ChangeServerRequested)
						{
							return null;
						}
					}
				}
				else
				{
					problem = $"Die Adresse \"{url}\" ist ungültig.";
				}
			}

			askForUrl = false;
			var dialog = new ServerSettingsWindow(url, problem, choice.Source);
			if (dialog.ShowDialog() != true || dialog.ServerUri is null)
			{
				return null;
			}

			url = dialog.ServerUri.ToString();
			var settings = settingsService.Load();
			settings.ApiUrl = url;
			settingsService.Save(settings);
		}
	}
}
