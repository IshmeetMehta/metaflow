

### `README.md`

```markdown
# GKE Distributed Hyperparameter Tuning with Metaflow & PyTorch

This repository contains a production-ready, horizontally scalable hyperparameter tuning workflow for a PyTorch convolutional neural network (CNN) trained on the CIFAR-10 dataset. 

The pipeline runs fully remote on **Google Kubernetes Engine (GKE)** via **Metaflow**, leveraging a cost-optimized **Spot node pool with dual NVIDIA L4 GPUs (`g2-standard-24`)**. Datasets are managed natively inside the cluster via a **Google Cloud Storage (GCS) Fuse PersistentVolumeClaim (PVC)** to ensure fast, shared, cache-friendly data streaming.

---

## Architecture Overview

1. **Local Client (Laptop/CI):** Compiles the orchestration blueprint and submits the workflow to the remote Metaflow cluster server.
2. **GKE Orchestrator Pod:** Executes the root workflow topology graph steps (`start`, `join`, `end`).
3. **Parallel GPU Worker Pods:** The `train` and `evaluate_model` steps fan out concurrently into distinct pods. They utilize isolated resource slices (`gpu=1` out of 2) on a single `g2-standard-24` Spot machine instance to maximize density.
4. **GCS Fuse Volume Mount:** The CIFAR-10 dataset is dynamically cached into a shared GCS bucket and mounted locally to workers at `/mnt/data`, completely removing duplicate web download overheads during matrix execution.

---

## Project Layout

```text
├── gcs-pvc.yaml           # Kubernetes static PV and PVC configuration
├── scale_tuning_gpu.py    # Metaflow DAG orchestration & GKE resource tracking
└── torch_steps.py         # PyTorch Model structure, training loop & inference hooks

```

---

## Storage & Namespace Boundaries

In Kubernetes, PersistentVolumeClaims (PVCs) are isolated by namespaces and cannot be natively cross-mounted by pods residing in a different namespace.

Because the `csi-gcs-dataset-pvc` is deployed within the dedicated `metaflow` namespace, **all execution pods launched by this workflow must be routed into the `metaflow` namespace**. If run inside the default namespace, the pods will fail to initialize with a `MountVolume.SetUp failed` error.

---

## Infrastructure Prerequisites

### 0. Enable the GCS FUSE CSI Driver

Before using GCS FUSE, you must enable the CSI driver on your GKE cluster:

```bash
gcloud container clusters update metaflow-cluster \
    --update-addons=GcsFuseCsiDriver=ENABLED \
    --location=us-central1-a
```

Verify that the driver pods are running in the `kube-system` namespace:

```bash
kubectl get pods -n kube-system | grep gcsfuse
```

### 1. Create the GKE Spot Node Pool

Provision the dual-GPU L4 nodes inside your existing GKE cluster with autoscaling enabled down to `0` when idle:

```bash
gcloud container node-pools create spot-2xl4-gpu-pool \
    --cluster=metaflow-cluster \
    --zone=us-central1-a \
    --machine-type=g2-standard-24 \
    --accelerator=type=nvidia-l4,count=2,gpu-driver-version=latest \
    --spot \
    --num-nodes=1 \
    --enable-autoscaling \
    --min-nodes=0 \
    --max-nodes=3 \
    --node-taints=[cloud.google.com/gke-spot=](https://cloud.google.com/gke-spot=)"true":NoSchedule,[nvidia.com/gpu=](https://nvidia.com/gpu=)"present":NoSchedule

```

### 2. Configure the GCS Bucket and IAM

Create the cloud dataset storage home and bind your cluster's Workload Identity account space to authorize runtime reading/writing:

```bash
# Create the storage bucket
gcloud storage buckets create gs://metaflow-cifar10-dataset --location=us-central1

# 1. Create the Kubernetes Service Account
kubectl create serviceaccount ksa-metaflow -n metaflow

# 2. Link the Kubernetes Service Account to the Google Service Account
gcloud iam service-accounts add-iam-policy-binding metaflow-service-account@platform-sandbox-495413.iam.gserviceaccount.com \
    --role=roles/iam.workloadIdentityUser \
    --member="serviceAccount:platform-sandbox-495413.svc.id.goog[metaflow/ksa-metaflow]"

# 3. Grant the Identity access to the storage bucket
gcloud storage buckets add-iam-policy-binding gs://metaflow-cifar10-dataset \
    --member="serviceAccount:metaflow-service-account@platform-sandbox-495413.iam.gserviceaccount.com" \
    --role="roles/storage.objectUser"

```

### 3. Deploy the Storage Mount to GKE

Apply the Persistent Volume Claim manifest to mount the GCS bucket locally into your workspace namespace:

```bash
kubectl create namespace metaflow
kubectl apply -f gcs-pvc.yaml

```

---

## Step-by-Step Execution Guide

### Step 1: Ensure Local Dependencies Exist

Your active local terminal shell requires the Kubernetes core library to establish the initial pipeline connection:

```bash
/usr/bin/python -m pip install --user kubernetes

```

### Step 2: Launch the GKE Pipeline inside the Storage Namespace

Execute the full execution lifecycle in the cloud, explicitly appending `namespace=metaflow` to the orchestration environment to unlock access to your PVC boundary:

# 1. Clear out the stale jobs
kubectl delete jobs --all -n metaflow

# 2. Fire off the execution run
METAFLOW_KUBERNETES_PIP_PACKAGES="kubernetes" python scale_tuning_gpu.py \
    --environment=local \
    --with kubernetes:namespace=metaflow run

---

## Cluster Monitoring

While the training loop is executing, you can watch your pods attach to the mounted GCS file system inside the namespace via `kubectl`:

```bash
# Verify the PVC status is 'Bound'
kubectl get pvc -n metaflow

# Track pod creation and status lifecycles 
kubectl get pods -n metaflow -w

```

```

```