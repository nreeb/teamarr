# Teamarr

Dynamic EPG Generator for Sports Channels

## Quick Start

```yaml
services:
  teamarr:
    image: ghcr.io/pharaoh-labs/teamarr:latest
    container_name: teamarr
    restart: unless-stopped
    ports:
      - 9195:9195
    volumes:
      - ./data:/app/data
    environment:
      - TZ=America/Detroit
```

```bash
docker compose up -d
```

## Image Tags

| Tag | Description |
|-----|-------------|
| `latest` | Stable release |
| `dev` | Development builds |
| `1.4.9-archive` | V1 archive (for migration) |

## Documentation

**User Guide**: https://teamarr-v2.jesmann.com/

Formal documentation coming soon.

## License

MIT
