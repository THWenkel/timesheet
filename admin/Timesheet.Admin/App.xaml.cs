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

		var apiUrl = Environment.GetEnvironmentVariable("TIMESHEET_API_URL")
			?? "http://localhost:8000/";
		if (!apiUrl.EndsWith('/'))
		{
			apiUrl += '/';
		}

		// The session is an HttpOnly cookie; the CSRF handler echoes the CSRF cookie in a header.
		var cookies = new CookieContainer();
		var baseUri = new Uri(apiUrl);
		var handler = new CsrfHandler(cookies, baseUri)
		{
			InnerHandler = new HttpClientHandler { CookieContainer = cookies, UseCookies = true },
		};
		var httpClient = new HttpClient(handler) { BaseAddress = baseUri };

		// Nothing works without a login: keep the app alive until the dialog is done.
		ShutdownMode = ShutdownMode.OnExplicitShutdown;
		var authApiClient = new AuthApiClient(httpClient);
		// While AUTH_ENABLED=false on the server (first setup: create the administrator
		// accounts and one-time passwords) no login is needed or possible to enforce.
		if (await authApiClient.IsAuthEnabledAsync()
			&& new LoginWindow(authApiClient).ShowDialog() != true)
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
			new BackupWindowService(backupApiClient, dialogService, new SettingsService()));

		MainWindow = new MainWindow { DataContext = viewModel };
		ShutdownMode = ShutdownMode.OnMainWindowClose;
		MainWindow.Show();
		viewModel.LoadCommand.Execute(null);
	}
}

