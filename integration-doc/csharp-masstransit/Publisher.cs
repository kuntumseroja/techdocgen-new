using System;
using System.Threading.Tasks;
using MassTransit;

namespace IntegrationDemo.Messaging
{
    public class Publisher
    {
        private readonly IPublishEndpoint _publisher;
        private readonly ISendEndpointProvider _sender;

        public Publisher(IPublishEndpoint publisher, ISendEndpointProvider sender)
        {
            _publisher = publisher;
            _sender = sender;
        }

        public async Task PublishOrderCreated(string orderId)
        {
            await _publisher.Publish(new OrderCreated { OrderId = orderId });
        }

        public async Task SendOrderCreated(string orderId)
        {
            var endpoint = await _sender.GetSendEndpoint(new Uri("queue:order-created"));
            await endpoint.Send(new OrderCreated { OrderId = orderId });
        }
    }
}
