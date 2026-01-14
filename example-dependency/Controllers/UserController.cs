using System;
using System.Collections.Generic;
using MyApp.Models;
using MyApp.Services;
using MyApp.Repositories;
using MyApp.Common;

namespace MyApp.Controllers
{
    /// <summary>
    /// Main controller for handling user requests
    /// </summary>
    public class UserController
    {
        private readonly IUserService _userService;
        private readonly ILogger _logger;

        public UserController(IUserService userService, ILogger logger)
        {
            _userService = userService;
            _logger = logger;
        }

        public User GetUser(int userId)
        {
            _logger.LogInfo($"Fetching user with ID: {userId}");
            return _userService.GetUserById(userId);
        }

        public List<User> GetAllUsers()
        {
            return _userService.GetAllUsers();
        }

        public void CreateUser(User user)
        {
            _userService.CreateUser(user);
            _logger.LogInfo($"Created new user: {user.Name}");
        }
    }
}
