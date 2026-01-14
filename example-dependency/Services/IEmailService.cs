namespace MyApp.Services
{
    /// <summary>
    /// Interface for email service operations
    /// </summary>
    public interface IEmailService
    {
        void SendWelcomeEmail(string email);
        void SendNotificationEmail(string email, string subject, string body);
    }
}
