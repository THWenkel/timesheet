using System.Windows;

namespace Timesheet.Admin.Views;

public partial class ProjectManagementWindow : Window
{
    public ProjectManagementWindow()
    {
        InitializeComponent();
    }

    private void Exit_Click(object sender, RoutedEventArgs e) => Close();
}