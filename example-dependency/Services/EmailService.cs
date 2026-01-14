using System;
using System.Net.Mail;

namespace MyApp.Services
{
    /// <summary>
    /// Email service implementation
    /// </summary>
    public class EmailService : IEmailService
    {
        private readonly SmtpClient _smtpClient;

        public EmailService(SmtpClient smtpClient)
        {
            _smtpClient = smtpClient;
        }

        public void SendWelcomeEmail(string email)
        {
            var message = new MailMessage("noreply@myapp.com", email)
            {
                Subject = "Welcome to MyApp",
                Body = "Thank you for joining MyApp!"
            };
            _smtpClient.Send(message);
        }

        public void SendNotificationEmail(string email, string subject, string body)
        {
            var message = new MailMessage("noreply@myapp.com", email)
            {
                Subject = subject,
                Body = body
            };
            _smtpClient.Send(message);
        }
    }
}
