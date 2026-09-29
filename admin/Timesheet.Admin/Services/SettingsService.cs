using System.IO;
using System.Text.Json;

namespace Timesheet.Admin.Services;

public sealed class AppSettings
{
    public string? BackupFolder { get; set; }
}

public interface ISettingsService
{
    AppSettings Load();
    void Save(AppSettings settings);
}

/// <summary>Remembers user choices (e.g. the backup folder) in %APPDATA%\Timesheet.Admin.</summary>
public sealed class SettingsService : ISettingsService
{
    private static readonly string FilePath = Path.Combine(
        Environment.GetFolderPath(Environment.SpecialFolder.ApplicationData),
        "Timesheet.Admin",
        "settings.json");

    public AppSettings Load()
    {
        try
        {
            return File.Exists(FilePath)
                ? JsonSerializer.Deserialize<AppSettings>(File.ReadAllText(FilePath)) ?? new AppSettings()
                : new AppSettings();
        }
        catch (Exception exception) when (exception is IOException or JsonException or UnauthorizedAccessException)
        {
            return new AppSettings();
        }
    }

    public void Save(AppSettings settings)
    {
        try
        {
            Directory.CreateDirectory(Path.GetDirectoryName(FilePath)!);
            File.WriteAllText(FilePath, JsonSerializer.Serialize(settings));
        }
        catch (Exception exception) when (exception is IOException or UnauthorizedAccessException)
        {
            // Not being able to remember the folder must never break a backup.
        }
    }
}
