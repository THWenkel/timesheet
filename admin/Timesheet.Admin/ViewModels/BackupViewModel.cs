using System.Collections.ObjectModel;
using System.IO;
using System.Net.Http;
using System.Text;
using System.Text.RegularExpressions;
using CommunityToolkit.Mvvm.ComponentModel;
using CommunityToolkit.Mvvm.Input;
using Timesheet.Admin.Models;
using Timesheet.Admin.Services;

namespace Timesheet.Admin.ViewModels;

public partial class BackupTableItem(BackupTableInfo info) : ObservableObject
{
    public string Name { get; } = info.Name;

    public string BackupTable { get; } = info.BackupTable;

    public int RowCount { get; } = info.RowCount;

    public string BackupState => info.BackupExists
        ? $"{info.BackupRowCount} Zeilen"
        : "Tabelle fehlt (Migration 009)";

    [ObservableProperty]
    private bool isSelected = true;
}

public partial class BackupViewModel(
    IBackupApiClient backupApiClient,
    IUserDialogService dialogService,
    ISettingsService settingsService) : ObservableObject
{
    // <table>_<yyyyMMdd_HHmmss>.<csv|json>
    private static readonly Regex FileNamePattern =
        new(@"^(?<table>.+)_\d{8}_\d{6}\.(?<ext>csv|json)$", RegexOptions.IgnoreCase);

    [ObservableProperty]
    private ObservableCollection<BackupTableItem> tables = [];

    [ObservableProperty]
    private bool exportCsv = true;

    [ObservableProperty]
    private bool exportJson = true;

    [ObservableProperty]
    [NotifyCanExecuteChangedFor(nameof(LoadCommand))]
    [NotifyCanExecuteChangedFor(nameof(BackupToDatabaseCommand))]
    [NotifyCanExecuteChangedFor(nameof(BackupToFilesCommand))]
    [NotifyCanExecuteChangedFor(nameof(RestoreFromDatabaseCommand))]
    [NotifyCanExecuteChangedFor(nameof(RestoreFromFilesCommand))]
    private bool isBusy;

    [ObservableProperty]
    private string? errorMessage;

    [ObservableProperty]
    private string statusText = "Bereit";

    [ObservableProperty]
    private string? backupFolder = settingsService.Load().BackupFolder;

    private bool IsNotBusy() => !IsBusy;

    [RelayCommand(CanExecute = nameof(IsNotBusy))]
    private async Task LoadAsync()
    {
        await RunAsync(async () =>
        {
            var infos = await backupApiClient.GetTablesAsync();
            Tables = new ObservableCollection<BackupTableItem>(infos.Select(info => new BackupTableItem(info)));
            StatusText = $"{Tables.Count} Tabellen geladen";
        });
    }

    [RelayCommand]
    private void SelectAll() => SetSelection(true);

    [RelayCommand]
    private void SelectNone() => SetSelection(false);

    private void SetSelection(bool value)
    {
        foreach (var table in Tables)
        {
            table.IsSelected = value;
        }
    }

    [RelayCommand(CanExecute = nameof(IsNotBusy))]
    private async Task BackupToDatabaseAsync()
    {
        var selected = SelectedTables();
        if (selected.Count == 0)
        {
            ErrorMessage = "Bitte mindestens eine Tabelle auswählen.";
            return;
        }

        await RunAsync(async () =>
        {
            var response = await backupApiClient.BackupToDbAsync(selected);
            var rows = response.Results.Sum(result => result.Rows);
            await ReloadTablesAsync();
            StatusText = $"Sicherung in Datenbank abgeschlossen: {response.Results.Count} Tabellen, {rows} Zeilen";
        });
    }

    [RelayCommand(CanExecute = nameof(IsNotBusy))]
    private async Task BackupToFilesAsync()
    {
        var selected = SelectedTables();
        var formats = SelectedFormats();
        if (selected.Count == 0 || formats.Count == 0)
        {
            ErrorMessage = "Bitte mindestens eine Tabelle und ein Format (CSV/JSON) auswählen.";
            return;
        }

        var folder = AskForFolder();
        if (folder is null)
        {
            return;
        }

        await RunAsync(async () =>
        {
            var files = await ExportToFolderAsync(selected, formats, folder);
            StatusText = $"{files} Dateien gesichert in {folder}";
        });
    }

    [RelayCommand(CanExecute = nameof(IsNotBusy))]
    private async Task RestoreFromDatabaseAsync()
    {
        var selected = SelectedTables();
        if (selected.Count == 0)
        {
            ErrorMessage = "Bitte mindestens eine Tabelle zur Wiederherstellung auswählen.";
            return;
        }

        await RunAsync(async () =>
        {
            var preview = await backupApiClient.RestoreFromDbAsync(selected, confirm: false, dryRun: true);
            if (!dialogService.ConfirmRestore("Datenbank-Sicherung (*_backup Tabellen)", Describe(preview.Results)))
            {
                StatusText = "Wiederherstellung abgebrochen";
                return;
            }

            if (!await SafetyExportAsync(selected))
            {
                StatusText = "Wiederherstellung abgebrochen";
                return;
            }

            var response = await backupApiClient.RestoreFromDbAsync(selected, confirm: true, dryRun: false);
            await ReloadTablesAsync();
            StatusText = $"Wiederherstellung abgeschlossen: {response.Results.Count} Tabellen";
        });
    }

    [RelayCommand(CanExecute = nameof(IsNotBusy))]
    private async Task RestoreFromFilesAsync()
    {
        var paths = dialogService.PickFiles(BackupFolder);
        if (paths is null || paths.Count == 0)
        {
            return;
        }

        await RunAsync(async () =>
        {
            var files = await ReadBackupFilesAsync(paths);
            var previews = new List<RestoreTableResult>();
            foreach (var file in files)
            {
                var preview = await backupApiClient.RestoreFromFileAsync(file, confirm: false, dryRun: true);
                previews.AddRange(preview.Results);
            }

            var names = string.Join(", ", files.Select(file => Path.GetFileName(file.Path)));
            if (!dialogService.ConfirmRestore($"Dateien: {names}", Describe(previews)))
            {
                StatusText = "Wiederherstellung abgebrochen";
                return;
            }

            if (!await SafetyExportAsync(files.Select(file => file.Table).Distinct().ToList()))
            {
                StatusText = "Wiederherstellung abgebrochen";
                return;
            }

            foreach (var file in files)
            {
                await backupApiClient.RestoreFromFileAsync(file, confirm: true, dryRun: false);
            }

            await ReloadTablesAsync();
            StatusText = $"Wiederherstellung abgeschlossen: {files.Count} Dateien";
        });
    }

    private async Task<List<BackupFile>> ReadBackupFilesAsync(IReadOnlyList<string> paths)
    {
        var known = Tables.Select(table => table.Name).ToHashSet(StringComparer.Ordinal);
        var files = new List<BackupFile>();
        foreach (var path in paths)
        {
            var match = FileNamePattern.Match(Path.GetFileName(path));
            if (!match.Success || !known.Contains(match.Groups["table"].Value))
            {
                throw new InvalidOperationException(
                    $"Dateiname nicht erkannt: {Path.GetFileName(path)} (erwartet: <tabelle>_<yyyyMMdd_HHmmss>.csv|json)");
            }

            var content = await File.ReadAllTextAsync(path, Encoding.UTF8);
            files.Add(new BackupFile(
                path,
                match.Groups["table"].Value,
                match.Groups["ext"].Value.ToLowerInvariant(),
                content));
        }

        // Parents before children, same order as the table list.
        var order = Tables.Select(table => table.Name).ToList();
        return files.OrderBy(file => order.IndexOf(file.Table)).ToList();
    }

    // Before anything is overwritten, the current state of the affected tables goes to files.
    private async Task<bool> SafetyExportAsync(IReadOnlyList<string> tableNames)
    {
        var folder = AskForFolder("Ordner für die Sicherheitskopie VOR der Wiederherstellung wählen");
        if (folder is null)
        {
            return false;
        }

        var files = await ExportToFolderAsync(tableNames, ["json"], folder);
        StatusText = $"Sicherheitskopie: {files} Dateien in {folder}";
        return true;
    }

    private async Task<int> ExportToFolderAsync(
        IReadOnlyList<string> tableNames,
        IReadOnlyList<string> formats,
        string folder)
    {
        Directory.CreateDirectory(folder);
        var stamp = DateTime.Now.ToString("yyyyMMdd_HHmmss");
        var count = 0;
        foreach (var table in tableNames)
        {
            foreach (var format in formats)
            {
                var bytes = await backupApiClient.ExportAsync(table, format);
                var path = Path.Combine(folder, $"{table}_{stamp}.{format}");
                // CreateNew: an existing backup file is never overwritten.
                await using var stream = new FileStream(path, FileMode.CreateNew, FileAccess.Write);
                await stream.WriteAsync(bytes);
                count++;
            }
        }

        return count;
    }

    private string? AskForFolder(string? title = null)
    {
        var folder = dialogService.PickFolder(BackupFolder, title);
        if (folder is not null)
        {
            BackupFolder = folder;
            settingsService.Save(new AppSettings { BackupFolder = folder });
        }

        return folder;
    }

    private static string Describe(IEnumerable<RestoreTableResult> results) =>
        string.Join(
            Environment.NewLine,
            results.Select(result =>
                $"• {result.Table}: {result.SourceRows} Datensätze in der Sicherung, " +
                $"{result.Updated} werden überschrieben, {result.Inserted} neu eingefügt"));

    private List<string> SelectedTables() =>
        Tables.Where(table => table.IsSelected).Select(table => table.Name).ToList();

    private List<string> SelectedFormats()
    {
        var formats = new List<string>();
        if (ExportCsv)
        {
            formats.Add("csv");
        }

        if (ExportJson)
        {
            formats.Add("json");
        }

        return formats;
    }

    private async Task ReloadTablesAsync()
    {
        var infos = await backupApiClient.GetTablesAsync();
        var previouslySelected = Tables.Where(table => table.IsSelected).Select(table => table.Name).ToHashSet();
        Tables = new ObservableCollection<BackupTableItem>(
            infos.Select(info => new BackupTableItem(info) { IsSelected = previouslySelected.Contains(info.Name) }));
    }

    private async Task RunAsync(Func<Task> operation)
    {
        IsBusy = true;
        ErrorMessage = null;
        StatusText = "Wird verarbeitet …";
        try
        {
            await operation();
        }
        catch (HttpRequestException exception)
        {
            ErrorMessage = $"Die Timesheet-API meldet einen Fehler: {exception.Message}";
            StatusText = "Fehler";
        }
        catch (Exception exception)
        {
            ErrorMessage = exception.Message;
            StatusText = "Fehler";
        }
        finally
        {
            IsBusy = false;
        }
    }
}
