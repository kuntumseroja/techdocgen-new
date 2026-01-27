"""Infra config flow extractor for RabbitMQ (JSON/YAML)"""

import json
from typing import Dict, List, Any
import yaml


class InfraConfigFlowExtractor:
    """Extract exchanges, queues, and bindings from infra config files"""
    
    def extract(self, content: str) -> Dict[str, Any]:
        data = self._parse_content(content)
        if not isinstance(data, dict):
            return {}
        rabbit = data.get("rabbitmq") or data.get("amqp") or {}
        if not isinstance(rabbit, dict):
            return {}
        
        exchanges = self._extract_exchanges(rabbit, data)
        queues = self._extract_queues(rabbit)
        bindings = self._extract_bindings(rabbit)
        
        return {
            "exchanges": exchanges,
            "queues": queues,
            "bindings": bindings
        }
    
    def _parse_content(self, content: str) -> Any:
        try:
            return json.loads(content)
        except Exception:
            pass
        try:
            return yaml.safe_load(content)
        except Exception:
            return None
    
    def _extract_exchanges(self, rabbit: Dict[str, Any], root: Dict[str, Any]) -> List[Dict[str, Any]]:
        exchanges = []
        for exchange in rabbit.get("exchanges", []) or []:
            if isinstance(exchange, dict) and exchange.get("name"):
                exchanges.append({
                    "name": exchange.get("name"),
                    "type": exchange.get("type", "")
                })
        for topic in rabbit.get("topics", []) or []:
            if isinstance(topic, dict) and topic.get("name"):
                exchanges.append({
                    "name": topic.get("name"),
                    "type": topic.get("type", "topic")
                })
        for topic in root.get("topics", []) or []:
            if isinstance(topic, dict) and topic.get("name"):
                exchanges.append({
                    "name": topic.get("name"),
                    "type": topic.get("type", "topic")
                })
        return exchanges
    
    def _extract_queues(self, rabbit: Dict[str, Any]) -> List[Dict[str, Any]]:
        queues = []
        for queue in rabbit.get("queues", []) or []:
            if isinstance(queue, dict) and queue.get("name"):
                queues.append({
                    "name": queue.get("name"),
                    "durable": queue.get("durable", False)
                })
        return queues
    
    def _extract_bindings(self, rabbit: Dict[str, Any]) -> List[Dict[str, Any]]:
        bindings = []
        for queue in rabbit.get("queues", []) or []:
            if not isinstance(queue, dict):
                continue
            binding = queue.get("binding")
            if isinstance(binding, dict):
                bindings.append({
                    "queue": queue.get("name", ""),
                    "exchange": binding.get("exchange", ""),
                    "routing_key": binding.get("routing_key", "")
                })
        return bindings
