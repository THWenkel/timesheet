using System.Windows;

namespace Timesheet.Admin.Views;

public partial class CustomerManagementWindow : Window
{
    public CustomerManagementWindow()
    {
        InitializeComponent();
    }

    private void Exit_Click(object sender, RoutedEventArgs e) => Close();
}