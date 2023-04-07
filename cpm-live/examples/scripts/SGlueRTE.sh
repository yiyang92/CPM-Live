#! /bin/bash
NNODES=1
MASTER_ADDR=localhost
MASTER_PORT=12345

# Remember to set environment variables e.g.:
# DATASET_PATH=/home/lyy92/Downloads/data/RTE
# OUTPUT_PATH=/home/lyy92/Projects/CPM-Live

OPTS=""
OPTS+=" --dataset-name SGlueRTE"
OPTS+=" --dataset-path $DATASET_PATH"
OPTS+=" --output-path $OUTPUT_PATH"
OPTS+=" --model-path $MODEL_PATH"
OPTS+=" --config-path $MODEL_CONFIG_PATH"
OPTS+=" --batch-size 32"
OPTS+=" --early-stop-patience 10"
OPTS+=" --eval-interval 50"
OPTS+=" --tune-maxlen 256"
OPTS+=" --lr 5e-3"
OPTS+=" --warmup-iters 50"
OPTS+=" --epochs 20"
OPTS+=" --infer-maxlen 1"

TUNE_CMD="torchrun --nnodes=${NNODES} --nproc_per_node=${GPUS_PER_NODE} --rdzv_id=1 --rdzv_backend=c10d --rdzv_endpoint=${MASTER_ADDR}:${MASTER_PORT} tune_cpm_ant.py ${OPTS}"

echo ${TUNE_CMD}
$TUNE_CMD

# INFER_CMD="python -u infer_cpm_ant.py ${OPTS}"
# echo ${INFER_CMD}
# $INFER_CMD
