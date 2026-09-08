# Enterprise Deployment / 企業部署

v0.4 提供 Helm chart：

```text
deploy/helm/multi-llm-ai-gateway
```

## Secret contract

先建立 Kubernetes Secret：

```bash
kubectl create secret generic multi-llm-ai-gateway-secrets \
  --from-literal=gateway-api-key='<gateway-key>' \
  --from-literal=admin-api-key='<admin-key>' \
  --from-literal=redis-url='redis://redis:6379/0'
```

Provider key 可選：

```text
openai-api-key
anthropic-api-key
google-api-key
```

## Install

```bash
helm lint deploy/helm/multi-llm-ai-gateway

helm upgrade --install ai-gateway \
  deploy/helm/multi-llm-ai-gateway \
  --set image.repository=<registry>/multi-llm-ai-gateway \
  --set image.tag=0.4.0
```

## Production defaults

Chart 預設包含：

- 2 replicas
- ClusterIP Service
- `/health` liveness
- `/ready` readiness
- CPU/memory requests and limits
- non-root pod security context
- drop all Linux capabilities
- read-only root filesystem
- PodDisruptionBudget
- Prometheus scrape annotations
- optional HPA
- optional Ingress

Redis 應使用企業既有 managed Redis / HA Redis，並啟用 authentication、TLS、backup 與 monitoring。
