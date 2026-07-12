# Changelog

## 0.3.0

- Add explicit `base.channel:name` zone addressing for sparse and multi-base installations
- Support the full documented master plus four-slave topology of 60 zones
- Treat uninitialised and standby values as unknown without repetitive error logs
- Reject empty, duplicate, malformed, and out-of-range zone entries during setup
- Add automated unit, HACS, hassfest, Python, and JSON validation
