#!/bin/bash
# Uranus: a Maya pack against the FP8 model - KL / same-top-token / NLL on the held-out eval text (the reference
# calib.py wrote), then the loop test.   bash eval_v1.sh <pack dir>
set -u
P=$1
Q=/mnt/nvme/maya/quant
PY=$HOME/.venvs/gguf-convert/bin/python
cd /mnt/nvme/maya/src/tools/maya_quant
echo "$(date +%T) KL vs FP8: $P"
$PY -u kl_eval.py --pack $P --eval $Q/eval.npy --ref $Q/stats/ref_topk.npz --seqs 0,3,6,9,12,15,18,21 --len 1024
if [ -f loop_test.py ]; then
  echo "$(date +%T) loop test: $P"
  $PY -u loop_test.py --pack $P
fi
