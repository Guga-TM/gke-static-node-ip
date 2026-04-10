## Deployment guide

1. Create `values.yaml` file and set at least the following values: `projectId`, `gcpServiceAccount` and `nodesDesiredIps` (see default `helm/values.yaml` for examples)
2. Check latest available version of helm chart [here](https://github.com/Guga-TM/gke-static-node-ip/pkgs/container/charts%2Fgke-static-node-ip)
3. Assuming that your `values.yaml` file is at path `YOUR_PATH/values.yaml`, run `helm upgrade` command and check rendered manifests (you may want to change chart version to the one you found in step 2):
```
helm upgrade --install \
  -n gke-static-node-ip \
  --create-namespace \
  gke-static-node-ip \
  oci://ghcr.io/guga-tm/charts/gke-static-node-ip:2.2.1 \
  -f YOUR_PATH/values.yaml \
  --dry-run
```
4. Run without `--dry-run` flag to deploy

## App components

### Distributor

Converts `nodepool`->`desired ips set` mapping to a `node`->`desired ip` mapping. Updates `controller-config` configmap.

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

## Required values
- `projectId` - GCP Project ID
- `gcpServiceAccount` - GCP Service Account that will be used for sending requests to Google API
- `networkTier` - Network Tier which you use in your GCP Project. Must be one of `PREMIUM`,`STANDARD`. Set to `STANDARD` by default
- `nodesDesiredIps` - Configuration of 'nodes'->'IPs' mapping. See details and examples in `helm/values.yaml`

## Optional values
- `distributor.checkRateSeconds` - Interval between requests to check current nodes status on the Distributor. Default value is 60
- `controller.checkRateSeconds` - Interval between requests to check current IP address on the Controller. Default value is 15
- `<component>.logLevel` - one of `info`, `error`. Default value is `info`

## Note about permissions

This project assumes that you're using Workload Identity Federation in your GKE cluster. Please add required permissions for GCP Service Account that you specify in helm/values.yaml. Also don't forget to add IAM Policy Binding:

```
export SA_NAME="your-sa-name"
export PROJECT_ID="your-project-id"
gcloud iam service-accounts add-iam-policy-binding $SA_NAME@$PROJECT_ID.iam.gserviceaccount.com \
    --role roles/iam.workloadIdentityUser \
    --member "serviceAccount:$PROJECT_ID.svc.id.goog[gke-static-node-ip/gke-static-node-ip]" \
    --project "$PROJECT_ID"
```