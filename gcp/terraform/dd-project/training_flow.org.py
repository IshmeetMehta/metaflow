# training_flow.py
#
# V3.5 V2C: preproc -> train -> end.
# Trained on cng_rec_item_ranker_mtmlv3_v4 dataset with GRID engagement + SID prefix features.
#
# Metadata
#   - team: ml-platform
#   - model_description: predictor for nvml mtml v3.5 v2c dnn (PCVR/PATCR/PCTR)

from metaflow import (
    FlowSpec,
    step,
    environment,
    current,
    torchrun,
    kubernetes,
    timeout,
    retry,
)

IMAGE_ARGS = {
    "base_image": "us-west1-docker.pkg.dev/platform-sandbox-495413/spsearch-qualitycheck-metaflow-image/sp-search-firelight-qualitycheck:v1",
    "python_packages": [
        "fireworks-ai-rec==2.1.19",
        "dnn_fireworks==0.0.2",
    ],
}

ENV_ARGS = {
    "vars": {
        "PREDICTOR_NAME": "dsml-nv-store_item_ranker_mtml",
        "MODEL_NAME": "mtml_v3_v2c_grid_sid_seq_cvr_atcr_ctr",
        "OWNER": "steven.xu",
        "TEAM": "ml-platform",
        "SAVE_PARENT_DIR": "/mnt/mountpoint-s3/doordash-datalake-temp/lucent_integration/nvml/p13n/mtml_v3.5_v2c_grid_sid_cvr_atcr_ctr/",
        "CACHE_PATH": "/mnt/mountpoint-s3/doordash-datalake-temp/lucent_integration/nvml/p13n/mtml_v3.5_v2c_grid_sid_cvr_atcr_ctr/cache",
        "CACHE_VERSION": 1775520872,
        "TRAIN_DATALAKE_TABLE_NAME": "cng_rec_item_ranker_mtmlv3_v4",
        "VALIDATION_DATALAKE_TABLE_NAME": "cng_rec_item_ranker_mtmlv3_v4",
        "DATALAKE_TABLE_PATH": "prod/ml/datasets",
        "TRAIN_DATA_START_DATE": "2025-12-21",
        "TRAIN_DATA_END_DATE": "2026-03-21",
        "TRAIN_DATA_LOOKBACK_DAYS": 0,
        "TRAIN_DATA_OFFSET_DAYS": 0,
        "VALIDATION_DATA_START_DATE": "2026-03-21",
        "VALIDATION_DATA_END_DATE": "2026-03-22",
        "VALIDATION_DATA_LOOKBACK_DAYS": 0,
        "VALIDATION_DATA_OFFSET_DAYS": 0,
        "BATCH_SIZE": 2048,
        "EPOCHS": 3,
        "NUM_DATALOADER_WORKERS": 3,
        "SNAPSHOT_INDEX": "2",
        "BARRIER_TIMEOUT_MINUTES": "120",
        "TORCHELASTIC_EXIT_BARRIER_TIMEOUT": "7200",
    }
}

PERSISTENT_VOLUME_CLAIMS = {
    "doordash-datalake": "/mnt/mountpoint-s3/doordash-datalake",
    "doordash-datalake-temp": "/mnt/mountpoint-s3/doordash-datalake-temp",
    # "doordash-ml-models": "/mnt/doordash-ml-models",
    # "doordash-ml-models-adhoc": "/mnt/doordash-ml-models-adhoc",
}


class MtmlV35V2c(FlowSpec):
    @step
    def start(self):
        self.model_version = int(current.run.created_at.timestamp())
        self.flow_start_date = current.run.created_at.strftime("%Y-%m-%d")
        self.next(self.start_run_preproc_train)

    @step
    def start_run_preproc_train(self):
        # self.next(self.run_preproc_train, num_parallel=96)
        self.next(self.run_preproc_train, num_parallel=2)

    # @image(**IMAGE_ARGS)
    @environment(**ENV_ARGS)
    @kubernetes(
        cpu=8,
        memory=64000,
        image=IMAGE_ARGS["base_image"],
        namespace="metaflow",
        shared_memory=10000,
        annotations={"gke-gcsfuse/volumes": "true"},
        persistent_volume_claims=PERSISTENT_VOLUME_CLAIMS
    )
    @retry(times=2)
    @torchrun
    @step
    def run_preproc_train(self):
        import os

        os.environ["MODEL_VERSION"] = str(self.model_version)
        os.environ["LUCENT_JOB_START_DATE"] = self.flow_start_date
        current.torch.run(
            entrypoint="run_preproc.py",
            entrypoint_args={"preprocsplit": "train"},
        )
        self.next(self.end_run_preproc_train)

    @step
    def end_run_preproc_train(self, inputs):
        self.merge_artifacts(inputs)
        self.next(self.start_train)

    @step
    def start_train(self):
        # self.next(self.train, num_parallel=16)
        self.next(self.train, num_parallel=2)

    @timeout(hours=48)
    # @image(**IMAGE_ARGS)
    @environment(**ENV_ARGS)
    @kubernetes(
        cpu=48,
        gpu=4,
        memory=192000,
        namespace="metaflow",
        shared_memory=10000,
        image=IMAGE_ARGS["base_image"],
        annotations={"gke-gcsfuse/volumes": "true"},
        tolerations=[
            {"key": "cloud.google.com/gke-spot", "operator": "Equal", "value": "true", "effect": "NoSchedule"},
            {"key": "nvidia.com/gpu", "operator": "Equal", "value": "present", "effect": "NoSchedule"}
        ],
        node_selector={"cloud.google.com/gke-spot": "true"},
        persistent_volume_claims=PERSISTENT_VOLUME_CLAIMS
    )
    @retry(times=2)
    @torchrun
    @step
    def train(self):
        import os

        os.environ["MODEL_VERSION"] = str(self.model_version)
        os.environ["LUCENT_JOB_START_DATE"] = self.flow_start_date
        current.torch.run(entrypoint="train.py", entrypoint_args={})
        self.next(self.end_train)

    @step
    def end_train(self, inputs):
        self.merge_artifacts(inputs)
        self.next(self.end)

    @step
    def end(self):
        print(f"Workflow completely finished. Run context version processed: {self.model_version}")
        pass


if __name__ == "__main__":
    MtmlV35V2c()
