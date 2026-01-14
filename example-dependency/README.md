# .NET Example with Dependencies

This folder contains a complete .NET application example with clear dependency relationships between classes.

## Structure

```
example-dependency/
├── Controllers/
│   └── UserController.cs      # Main controller (depends on Services, Models, Common)
├── Models/
│   └── User.cs                 # User model and UserRole enum
├── Services/
│   ├── IUserService.cs         # User service interface
│   ├── UserService.cs          # User service (depends on Repositories, Services)
│   ├── IEmailService.cs        # Email service interface
│   └── EmailService.cs         # Email service implementation
├── Repositories/
│   ├── IUserRepository.cs      # User repository interface
│   ├── UserRepository.cs       # User repository (depends on Models, Repositories)
│   ├── IDatabaseContext.cs     # Database context interface
│   └── DatabaseContext.cs      # Database context implementation
└── Common/
    ├── ILogger.cs              # Logger interface
    └── ConsoleLogger.cs        # Logger implementation
```

## Dependency Flow

1. **UserController** → depends on:
   - `MyApp.Models` (User class)
   - `MyApp.Services` (IUserService)
   - `MyApp.Common` (ILogger)

2. **UserService** → depends on:
   - `MyApp.Models` (User)
   - `MyApp.Repositories` (IUserRepository)
   - `MyApp.Services` (IEmailService)

3. **UserRepository** → depends on:
   - `MyApp.Models` (User)
   - `MyApp.Repositories` (IDatabaseContext)

4. **EmailService** → depends on:
   - System.Net.Mail (external .NET library)

## Usage

When you run the dependency analysis on this folder, it should detect:
- Internal dependencies between your custom classes
- Cross-namespace dependencies (Models, Services, Repositories, Common)
- Multiple levels of dependency relationships
- Dependency chain: Controller → Service → Repository → Database Context
