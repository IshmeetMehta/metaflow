# scale_tuning_gpu.py
from metaflow import FlowSpec, step, Parameter, kubernetes, JSONType, retry
import json

class GKEGPUFlow(FlowSpec):
    
    learning_rates = Parameter(
        'learning-rates',
        default=json.dumps([0.01, 0.001, 0.0001]),
        type=JSONType
    )

    @step
    def start(self):
        # Begins the pipeline graph execution
        self.next(self.train, foreach='learning_rates')

    @kubernetes(
        cpu=4,         
        memory=16000,   
        gpu=1,          
        image="pytorch/pytorch:2.0.1-cuda11.7-cudnn8-runtime",
        # Routes the worker step pods directly into your storage cluster namespace boundary
        namespace="metaflow",
        # Mounts the GCS-backed file volume to a clean mock-local directory path
        persistent_volume_claims={"csi-gcs-dataset-pvc": "/mnt/data"},
        # Triggers GKE's native mutation webhook to inject the GCS Fuse proxy sidecar container
        annotations={"gke-gcsfuse/volumes": "true"},
        tolerations=[
            {"key": "cloud.google.com/gke-spot", "operator": "Equal", "value": "true", "effect": "NoSchedule"},
            {"key": "nvidia.com/gpu", "operator": "Equal", "value": "present", "effect": "NoSchedule"}
        ],
        node_selector={"cloud.google.com/gke-spot": "true"}
    )
    # Catches file-system race collisions ('Stale file handle') during parallel downloads
    # and re-runs the step once the sibling tasks finish populating the bucket cache.
    @retry(times=2)
    @step
    def train(self):
        import torch_steps 
        print(f"Executing training on GKE Spot L4 GPU. Learning rate: {self.input}")
        
        # Reads directly from or downloads to the shared persistent cluster path
        trainloader, _, _ = torch_steps.load_data(data_dir='/mnt/data')
        
        # Pulls state dictionary weights back onto host CPU memory before serialization
        self.model_state = torch_steps.train_model(
            trainloader,
            lr=self.input,
            epochs=2
        )
        self.next(self.evaluate_model)

    @kubernetes(
        cpu=4, 
        memory=16000, 
        gpu=1,
        image="pytorch/pytorch:2.0.1-cuda11.7-cudnn8-runtime",
        namespace="metaflow",
        persistent_volume_claims={"csi-gcs-dataset-pvc": "/mnt/data"},
        annotations={"gke-gcsfuse/volumes": "true"},
        tolerations=[
            {"key": "cloud.google.com/gke-spot", "operator": "Equal", "value": "true", "effect": "NoSchedule"},
            {"key": "nvidia.com/gpu", "operator": "Equal", "value": "present", "effect": "NoSchedule"}
        ],
        node_selector={"cloud.google.com/gke-spot": "true"}
    )
    @step
    def evaluate_model(self):
        import torch_steps 
        _, testloader, _ = torch_steps.load_data(data_dir='/mnt/data')
        
        result = torch_steps.run_inference_and_tests(
            self.model_state,
            testloader
        )
        self.accuracy = result
        self.next(self.join)

    # Completely safe on standard, low-cost CPU nodes since weights tensors
    # are decoupled from specific physical CUDA device streams during loading.
    @kubernetes(
        cpu=2,
        memory=4000,
        image="pytorch/pytorch:2.0.1-cuda11.7-cudnn8-runtime"
    )
    @step
    def join(self, inputs):
        best_score = -1
        self.best_state = None
        
        for i in inputs:
            print(f"Learning rate {i.input} achieved {i.accuracy}% accuracy.")
            if i.accuracy > best_score:
                best_score = i.accuracy
                self.best_state = i.model_state
                
        self.best_score = best_score
        print(f"--- Workflow Complete! Best model accuracy: {best_score}% ---")
        self.next(self.end)

    @step
    def end(self):
        print("Flow finished cleanly.")

if __name__ == '__main__':
    GKEGPUFlow()