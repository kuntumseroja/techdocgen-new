"""Config file parser for JSON/YAML - SRS FR-06, FR-07: Kubernetes, ELK, Redis, Hangfire, Consul"""

import json
import re
from typing import Dict, List, Any, Optional
import yaml
from .base_parser import BaseParser


class ConfigParser(BaseParser):
    """Parser for configuration files (JSON/YAML) including K8s manifests and infra configs"""
    
    def parse(self, code: str, file_path: str = "") -> Dict[str, Any]:
        """Parse configuration content with K8s (FR-06) and other infra (FR-07) support"""
        parsed = self._parse_content(code)
        result = {
            "config_type": parsed.get("type"),
            "top_level_keys": parsed.get("keys", []),
            "comments": self.extract_comments(code) if self.include_comments else []
        }
        # FR-06: Kubernetes manifests
        k8s = self._extract_kubernetes(parsed.get("data"), file_path)
        if k8s:
            result["kubernetes"] = k8s
        # FR-07: ELK, Redis, Hangfire, Consul
        infra = self._extract_infra_configs(parsed.get("data"), code)
        if infra:
            result["infra"] = infra
        return result
    
    def _parse_content(self, code: str) -> Dict[str, Any]:
        """Try parsing JSON, then YAML"""
        data = None
        try:
            data = json.loads(code)
            return {"type": "json", "keys": self._extract_keys(data), "data": data}
        except Exception:
            pass
        try:
            data = yaml.safe_load(code)
            return {"type": "yaml", "keys": self._extract_keys(data) if data else [], "data": data}
        except Exception:
            return {"type": "unknown", "keys": [], "data": None}
    
    def _extract_keys(self, data: Any) -> List[str]:
        """Extract top-level keys from parsed config"""
        if isinstance(data, dict):
            return list(data.keys())
        return []
    
    def _extract_kubernetes(self, data: Any, file_path: str) -> Optional[Dict[str, Any]]:
        """FR-06: Extract Deployment, Service, ConfigMap, Secret, Ingress, resource limits, health probes"""
        if not data:
            return None
        if isinstance(data, list):
            data = data[0] if data else None
        if not data or not isinstance(data, dict):
            return None
        kind = data.get("kind") or ""
        if not kind and "kind" not in str(data).lower():
            # Multi-document YAML
            return None
        kind = data.get("kind", "")
        if kind not in ("Deployment", "Service", "ConfigMap", "Secret", "Ingress", "StatefulSet", "DaemonSet"):
            return None
        result = {"kind": kind, "name": "", "metadata": {}}
        meta = data.get("metadata", {}) or {}
        result["name"] = meta.get("name", meta.get("generateName", ""))
        result["metadata"] = {k: v for k, v in meta.items() if k in ("name", "labels", "annotations")}
        if kind == "Deployment":
            spec = data.get("spec", {}) or {}
            template = spec.get("template", {}) or {}
            pod_spec = template.get("spec", {}) or {}
            containers = pod_spec.get("containers", []) or []
            result["containers"] = []
            for c in containers:
                cont = {"name": c.get("name", ""), "image": c.get("image", "")}
                resources = c.get("resources", {}) or {}
                limits = resources.get("limits", {}) or {}
                requests = resources.get("requests", {}) or {}
                cont["limits"] = limits
                cont["requests"] = requests
                probes = {}
                if c.get("livenessProbe"):
                    probes["liveness"] = _describe_probe(c["livenessProbe"])
                if c.get("readinessProbe"):
                    probes["readiness"] = _describe_probe(c["readinessProbe"])
                if probes:
                    cont["probes"] = probes
                result["containers"].append(cont)
        elif kind == "Service":
            spec = data.get("spec", {}) or {}
            result["type"] = spec.get("type", "ClusterIP")
            result["ports"] = spec.get("ports", [])
        elif kind == "Ingress":
            spec = data.get("spec", {}) or {}
            result["rules"] = spec.get("rules", [])
            result["tls"] = spec.get("tls", [])
        elif kind == "ConfigMap":
            result["data_keys"] = list((data.get("data") or {}).keys())
        elif kind == "Secret":
            result["data_keys"] = list((data.get("data") or {}).keys())
        return result
    
    def _extract_infra_configs(self, data: Any, code: str) -> Optional[Dict[str, Any]]:
        """FR-07: Extract ELK, Redis, Hangfire, Consul configs"""
        if not data and not code:
            return None
        result = {}
        data = data or {}
        if isinstance(data, dict):
            if "elasticsearch" in str(data).lower() or "logstash" in str(data).lower() or "kibana" in str(data).lower():
                result["elk"] = {
                    "elasticsearch": bool(data.get("elasticsearch") or "elasticsearch" in str(data).lower()),
                    "logstash": bool(data.get("logstash") or "logstash" in str(data).lower()),
                    "index_templates": _find_nested(data, "index", "template") or [],
                }
            if "redis" in str(data).lower():
                redis = data.get("redis") or data
                if isinstance(redis, dict):
                    result["redis"] = {"host": redis.get("host", redis.get("ConnectionString", ""))}
                elif isinstance(redis, str):
                    result["redis"] = {"connection": redis[:80] + "..." if len(redis) > 80 else redis}
            if "hangfire" in str(data).lower():
                result["hangfire"] = {"detected": True}
            if "consul" in str(data).lower():
                consul = data.get("consul") or data
                result["consul"] = {"address": consul.get("address", "") if isinstance(consul, dict) else "detected"}
        # Fallback: regex detection in raw code
        if "logstash" in code.lower() or "elasticsearch" in code.lower():
            result.setdefault("elk", {})["detected"] = True
        if re.search(r"redis[\"']?\s*:", code, re.I) or "ConnectionMultiplexer" in code:
            result.setdefault("redis", {})["detected"] = True
        if "UseHangfire" in code or "AddHangfire" in code:
            result.setdefault("hangfire", {})["detected"] = True
        if "ConsulClient" in code or "consul" in code.lower():
            result.setdefault("consul", {})["detected"] = True
        return result if result else None


def _describe_probe(probe: dict) -> str:
    """Describe a K8s probe configuration"""
    if probe.get("httpGet"):
        return f"HTTP {probe['httpGet'].get('path', '/')}"
    if probe.get("tcpSocket"):
        return "TCP"
    if probe.get("exec"):
        return "Exec"
    return "configured"


def _find_nested(d: dict, *keys: str) -> List:
    """Find nested keys in dict"""
    for k in keys:
        if isinstance(d, dict) and k in d:
            v = d[k]
            return v if isinstance(v, list) else [v]
        if isinstance(d, dict):
            for v in d.values():
                r = _find_nested(v, k) if isinstance(v, dict) else []
                if r:
                    return r
    return []
