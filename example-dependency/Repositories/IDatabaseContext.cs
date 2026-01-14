using System.Collections.Generic;
using MyApp.Models;

namespace MyApp.Repositories
{
    /// <summary>
    /// Database context interface
    /// </summary>
    public interface IDatabaseContext
    {
        ICollection<User> Users { get; }
        void SaveChanges();
    }
}
