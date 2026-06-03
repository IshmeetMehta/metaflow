from metaflow import FlowSpec, step

class HelloFlow(FlowSpec):
    @step
    def start(self):
        print("This flow number 3")
        self.next(self.end)

    @step
    def end(self):
        print("Done!")

if __name__ == '__main__':
    HelloFlow()
