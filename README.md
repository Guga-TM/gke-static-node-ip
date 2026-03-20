### GCP Permissions required to run this application
- compute.instances.addAccessConfig
- compute.instances.deleteAccessConfig
- compute.instances.get
- compute.instances.update
- compute.zones.list
- resourcemanager.projects.get

### Required ENV variables
- PROJECT_ID
- ZONE
- NETWORK_TIER
- DESIRED_IP

### Optional ENV variables
- LOG_LEVEL (one of `info`, `error`)