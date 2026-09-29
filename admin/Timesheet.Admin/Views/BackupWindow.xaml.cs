using System.Windows;

namespace Timesheet.Admin.Views;

public partial class BackupWindow : Window
{
    public BackupWindow()
    {
        InitializeComponent();
    }

    private void Exit_Click(object sender, RoutedEventArgs e) => Close();
}
