# scale_tuning_gpu.py
from metaflow import FlowSpec, step, Parameter, kubernetes, JSONType
import json

class GKEGPUFlow(FlowSpec):
    
    learning_rates = Parameter(
        'learning-rates',
        default=json.dumps([0.01, 0.001, 0.0001]),
        type=JSONType
    )

    @step
    def start(self):
        self.next(self.train, foreach='learning_rates')

    @kubernetes(
        cpu=4,         
        memory=16000,   
        gpu=1,          
        image="pytorch/pytorch:2.0.1-cuda11.7-cudnn8-runtime",
        tolerations=[
            {"key": "cloud.google.com/gke-spot", "operator": "Equal", "value": "true", "effect": "NoSchedule"},
            {"key": "nvidia.com/gpu", "operator": "Equal", "value": "present", "effect": "NoSchedule"}
        ],
        node_selector={"cloud.google.com/gke-spot": "true"}
    )
    @step
    def train(self):
        import torch_steps 
        print(f"Executing training on GKE Spot L4 GPU. Learning rate: {self.input}")
        
        trainloader, _, _ = torch_steps.load_data()
        
        # Saves the weights dict profile
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
        tolerations=[
            {"key": "cloud.google.com/gke-spot", "operator": "Equal", "value": "true", "effect": "NoSchedule"},
            {"key": "nvidia.com/gpu", "operator": "Equal", "value": "present", "effect": "NoSchedule"}
        ],
        node_selector={"cloud.google.com/gke-spot": "true"}
    )
    @step
    def evaluate_model(self):
        import torch_steps 
        _, testloader, _ = torch_steps.load_data()
        
        result = torch_steps.run_inference_and_tests(
            self.model_state,
            testloader
        )
        self.accuracy = result
        self.next(self.join)

    # Completely safe now on 2 standard CPUs!
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