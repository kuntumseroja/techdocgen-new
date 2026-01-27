"""amqplib (Node.js) flow extractor for RabbitMQ"""

import re
from typing import Dict, List, Any


class AmqplibFlowExtractor:
    """Extract RabbitMQ flows from Node.js amqplib usage"""
    
    ASSERT_EXCHANGE_PATTERN = re.compile(r'assertExchange\(\s*[\'"]([^\'"]+)[\'"]\s*,\s*[\'"]([^\'"]+)[\'"]')
    ASSERT_QUEUE_PATTERN = re.compile(r'assertQueue\(\s*[\'"]([^\'"]+)[\'"]')
    BIND_QUEUE_PATTERN = re.compile(r'bindQueue\(\s*[\'"]([^\'"]+)[\'"]\s*,\s*[\'"]([^\'"]+)[\'"]\s*(?:,\s*[\'"]([^\'"]+)[\'"])?')
    PUBLISH_PATTERN = re.compile(r'publish\(\s*[\'"]([^\'"]+)[\'"]\s*,\s*[\'"]([^\'"]*)[\'"]')
    SEND_TO_QUEUE_PATTERN = re.compile(r'sendToQueue\(\s*[\'"]([^\'"]+)[\'"]')
    CONSUME_PATTERN = re.compile(r'consume\(\s*[\'"]([^\'"]+)[\'"]')
    
    def extract(self, code: str) -> Dict[str, Any]:
        """Extract amqplib flows from Node.js code"""
        exchanges = self._extract_exchanges(code)
        queues = self._extract_queues(code)
        bindings = self._extract_bindings(code)
        publishes = self._extract_publishes(code)
        send_to_queue = self._extract_send_to_queue(code)
        consumes = self._extract_consumes(code)
        
        return {
            "exchanges": exchanges,
            "queues": queues,
            "bindings": bindings,
            "publishes": publishes,
            "send_to_queue": send_to_queue,
            "consumes": consumes
        }
    
    def _extract_exchanges(self, code: str) -> List[Dict[str, Any]]:
        exchanges = []
        for match in self.ASSERT_EXCHANGE_PATTERN.finditer(code):
            exchanges.append({
                "name": match.group(1),
                "type": match.group(2)
            })
        return exchanges
    
    def _extract_queues(self, code: str) -> List[Dict[str, Any]]:
        queues = []
        for match in self.ASSERT_QUEUE_PATTERN.finditer(code):
            queues.append({"name": match.group(1)})
        return queues
    
    def _extract_bindings(self, code: str) -> List[Dict[str, Any]]:
        bindings = []
        for match in self.BIND_QUEUE_PATTERN.finditer(code):
            bindings.append({
                "queue": match.group(1),
                "exchange": match.group(2),
                "routing_key": match.group(3) or ""
            })
        return bindings
    
    def _extract_publishes(self, code: str) -> List[Dict[str, Any]]:
        publishes = []
        for match in self.PUBLISH_PATTERN.finditer(code):
            publishes.append({
                "exchange": match.group(1),
                "routing_key": match.group(2)
            })
        return publishes
    
    def _extract_send_to_queue(self, code: str) -> List[Dict[str, Any]]:
        sends = []
        for match in self.SEND_TO_QUEUE_PATTERN.finditer(code):
            sends.append({"queue": match.group(1)})
        return sends
    
    def _extract_consumes(self, code: str) -> List[Dict[str, Any]]:
        consumes = []
        for match in self.CONSUME_PATTERN.finditer(code):
            consumes.append({"queue": match.group(1)})
        return consumes
