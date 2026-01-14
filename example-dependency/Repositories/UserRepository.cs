using System.Collections.Generic;
using System.Linq;
using MyApp.Models;

namespace MyApp.Repositories
{
    /// <summary>
    /// Repository implementation for user data access
    /// </summary>
    public class UserRepository : IUserRepository
    {
        private readonly IDatabaseContext _context;

        public UserRepository(IDatabaseContext context)
        {
            _context = context;
        }

        public User FindById(int id)
        {
            return _context.Users.FirstOrDefault(u => u.Id == id);
        }

        public IEnumerable<User> FindAll()
        {
            return _context.Users;
        }

        public void Save(User user)
        {
            _context.Users.Add(user);
            _context.SaveChanges();
        }

        public void Update(User user)
        {
            var existing = FindById(user.Id);
            if (existing != null)
            {
                existing.Name = user.Name;
                existing.Email = user.Email;
                existing.Role = user.Role;
                _context.SaveChanges();
            }
        }

        public void Delete(int id)
        {
            var user = FindById(id);
            if (user != null)
            {
                _context.Users.Remove(user);
                _context.SaveChanges();
            }
        }
    }
}
