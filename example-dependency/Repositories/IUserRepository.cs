using System.Collections.Generic;
using MyApp.Models;

namespace MyApp.Repositories
{
    /// <summary>
    /// Interface for user data repository operations
    /// </summary>
    public interface IUserRepository
    {
        User FindById(int id);
        IEnumerable<User> FindAll();
        void Save(User user);
        void Update(User user);
        void Delete(int id);
    }
}
