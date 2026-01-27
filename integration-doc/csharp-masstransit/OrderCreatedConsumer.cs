using System.Threading.Tasks;
using MassTransit;

namespace IntegrationDemo.Messaging
{
    public class OrderCreatedConsumer : IConsumer<OrderCreated>
    {
        public Task Consume(ConsumeContext<OrderCreated> context)
        {
            return Task.CompletedTask;
        }
    }
}
