using System.Net.Http;
using System.Windows;
using Timesheet.Admin.Services;
using Timesheet.Admin.ViewModels;

namespace Timesheet.Admin;

/// <summary>
/// Interaction logic for App.xaml
/// </summary>
public partial class App : Application
{
	protected override void OnStartup(StartupEventArgs e)
	{
		base.OnStartup(e);

		var apiUrl = Environment.GetEnvironmentVariable("TIMESHEET_API_URL")
			?? "http://localhost:8000/";
		if (!apiUrl.EndsWith('/'))
		{
			apiUrl += '/';
		}

		var httpClient = new HttpClient { BaseAddress = new Uri(apiUrl) };
		var employeeApiClient = new EmployeeApiClient(httpClient);
		var projectApiClient = new ProjectApiClient(httpClient);
		var dialogService = new UserDialogService();
		var viewModel = new MainWindowViewModel(
			employeeApiClient,
			projectApiClient,
			dialogService,
			new ProjectWindowService(projectApiClient, employeeApiClient, dialogService),
			new CustomerWindowService(projectApiClient, dialogService));

		MainWindow = new MainWindow { DataContext = viewModel };
		MainWindow.Show();
		viewModel.LoadCommand.Execute(null);
	}
}

