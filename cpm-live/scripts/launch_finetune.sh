#!/bin/bash

# GPU
export CUDA_VISIBLE_DEVICES=0
export GPUS_PER_NODE=1

USER=lyy92  # User on host machine
FINETUNE_SCRIPT="/home/$USER/Projects/CPM-Live/cpm-live/examples/scripts/SGlueRTE.sh"

# Finetune paths
export DATASET_PATH="/home/$USER/Downloads/data/RTE"
export OUTPUT_PATH="/home/$USER/Projects/CPM-Live"
export MODEL_PATH="/home/$USER/Downloads/data/models/cpm-ant-plus-10b/cpm-ant-plus-10b.pt"
export MODEL_CONFIG_PATH="/home/$USER/Downloads/data/models/cpm-ant-plus-10b/cpm-ant-plus-10b.json"

echo ${FINETUNE_SCRIPT}
chmod +x $FINETUNE_SCRIPT && $FINETUNE_SCRIPT
