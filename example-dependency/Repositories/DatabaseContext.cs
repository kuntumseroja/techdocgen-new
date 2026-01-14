using System.Collections.Generic;
using MyApp.Models;

namespace MyApp.Repositories
{
    /// <summary>
    /// Database context implementation
    /// </summary>
    public class DatabaseContext : IDatabaseContext
    {
        private readonly List<User> _users;

        public DatabaseContext()
        {
            _users = new List<User>();
        }

        public ICollection<User> Users => _users;

        public void SaveChanges()
        {
            // In a real implementation, this would persist to database
            // For this example, we'll just simulate persistence
        }
    }
}
