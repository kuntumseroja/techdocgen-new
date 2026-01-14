using System.Collections.Generic;
using System.Linq;
using MyApp.Models;
using MyApp.Repositories;

namespace MyApp.Services
{
    /// <summary>
    /// Service implementation for user operations
    /// </summary>
    public class UserService : IUserService
    {
        private readonly IUserRepository _userRepository;
        private readonly IEmailService _emailService;

        public UserService(IUserRepository userRepository, IEmailService emailService)
        {
            _userRepository = userRepository;
            _emailService = emailService;
        }

        public User GetUserById(int userId)
        {
            return _userRepository.FindById(userId);
        }

        public List<User> GetAllUsers()
        {
            return _userRepository.FindAll().ToList();
        }

        public void CreateUser(User user)
        {
            _userRepository.Save(user);
            _emailService.SendWelcomeEmail(user.Email);
        }

        public void UpdateUser(User user)
        {
            _userRepository.Update(user);
        }

        public void DeleteUser(int userId)
        {
            _userRepository.Delete(userId);
        }
    }
}
