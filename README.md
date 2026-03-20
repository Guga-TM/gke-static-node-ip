## App components

### Controller

Runs on each node where IP needs to be controlled. Sends requests to Fixer.

### Fixer

Runs on the nodes except the ones for which IP needs to be controlled. Sends requests to Google API to delete wrong IP and set desired IP.

## GCP Permissions required to run this application
- compute.instances.addAccessConfig
- compute.instances.deleteAccessConfig
- compute.instances.get
- compute.instances.list
- compute.instances.update
- compute.zones.list
- resourcemanager.projects.get

## Required ENV variables
- PROJECT_ID
- ZONE
- NETWORK_TIER
- DESIRED_IP

## Optional ENV variables
- LOG_LEVEL (one of `info`, `error`)