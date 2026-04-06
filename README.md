## App components

### Controller

Runs on each node where IP needs to be controlled. Sends requests to Fixer. Using [ipify.org](https://www.ipify.org/) as API for fetching current IP address.

### Fixer

Runs on the nodes except the ones for which IP needs to be controlled. Sends requests to Google API to delete wrong IP and set desired IP.

## Minimal GCP Permissions required to run Fixer component
- compute.addresses.use
- compute.instances.addAccessConfig
- compute.instances.deleteAccessConfig
- compute.instances.get
- compute.instances.list
- compute.instances.update
- compute.subnetworks.useExternalIp
- compute.zones.list
- resourcemanager.projects.get

## Required ENV variables
- `PROJECT_ID` - GCP Project ID
- `NETWORK_TIER` - Network Tier which you use in your GCP Project. Must be one of `PREMIUM`,`STANDARD`

## Optional ENV variables
- `LOG_LEVEL` - one of `info`, `error`
- `CHECK_RATE_SECONDS` - interval between requests to check current IP address on the Controller