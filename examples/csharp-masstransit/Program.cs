using MassTransit;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Hosting;

namespace Example.Messaging
{
    public class Program
    {
        public static void Main(string[] args)
        {
            Host.CreateDefaultBuilder(args)
                .ConfigureServices(services =>
                {
                    services.AddMassTransit(x =>
                    {
                        x.AddConsumer<OrderCreatedConsumer>();

                        x.UsingRabbitMq((context, cfg) =>
                        {
                            cfg.Host("localhost", "/", h =>
                            {
                                h.Username("guest");
                                h.Password("guest");
                            });

                            cfg.ReceiveEndpoint("order-created", e =>
                            {
                                e.Consumer<OrderCreatedConsumer>(context);
                            });
                        });
                    });
                })
                .Build()
                .Run();
        }
    }
}
