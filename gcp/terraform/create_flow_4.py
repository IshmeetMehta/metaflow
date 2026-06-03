from metaflow import FlowSpec, step, kubernetes

class GPUScaleFlow(FlowSpec):
    # Define hyperparameters to sweep over in parallel
    learning_rates = [0.01, 0.05, 0.1]

    @step
    def start(self):
        print("Starting parallel hyperparameter sweep on GPUs...")
        # Fan-out: Metaflow will launch a pod for each item in learning_rates
        self.next(self.train, foreach='learning_rates')

    @kubernetes(gpu=1, cpu=4, memory=16000) # Request 1 GPU, 4 CPUs, and 16GB RAM
    @step
    def train(self):
        # self.input contains the current learning rate from the foreach list
        self.lr = self.input
        print(f"Training model on GPU with learning_rate: {self.lr}")
        
        # Simulate training logic and results
        self.accuracy = 0.9 + (self.lr * 0.1)
        self.next(self.join)

    @step
    def join(self, inputs):
        # Fan-in: Collect results from all parallel training runs
        self.results = {inp.lr: inp.accuracy for inp in inputs}
        self.best_lr = max(self.results, key=self.results.get)
        self.next(self.end)

    @step
    def end(self):
        print(f"Sweep complete. Best LR: {self.best_lr} with accuracy {self.results[self.best_lr]}")

if __name__ == '__main__':
    GPUScaleFlow()