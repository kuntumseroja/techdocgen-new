using System.Collections.Generic;
using MyApp.Models;

namespace MyApp.Services
{
    /// <summary>
    /// Interface for user service operations
    /// </summary>
    public interface IUserService
    {
        User GetUserById(int userId);
        List<User> GetAllUsers();
        void CreateUser(User user);
        void UpdateUser(User user);
        void DeleteUser(int userId);
    }
}
