namespace MyApp.Common
{
    /// <summary>
    /// Logger interface
    /// </summary>
    public interface ILogger
    {
        void LogInfo(string message);
        void LogError(string message);
        void LogWarning(string message);
    }
}
