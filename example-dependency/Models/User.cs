using System;

namespace MyApp.Models
{
    /// <summary>
    /// Represents a user in the system
    /// </summary>
    public class User
    {
        public int Id { get; set; }
        public string Name { get; set; }
        public string Email { get; set; }
        public DateTime CreatedAt { get; set; }
        public UserRole Role { get; set; }

        public User()
        {
            CreatedAt = DateTime.Now;
        }

        public bool IsAdmin()
        {
            return Role == UserRole.Admin;
        }
    }

    /// <summary>
    /// User role enumeration
    /// </summary>
    public enum UserRole
    {
        Guest,
        User,
        Admin
    }
}
