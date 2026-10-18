#!/usr/bin/env python3
"""Minimal CUDA/ROCm all-reduce probe. Run with torchrun on prepared devices."""
import os
from datetime import timedelta

import torch
import torch.distributed as dist


def main():
    local_rank = int(os.environ['LOCAL_RANK'])
    torch.cuda.set_device(local_rank)
    dist.init_process_group('nccl', timeout=timedelta(seconds=60))
    try:
        value = torch.ones(1, device=f'cuda:{local_rank}')
        dist.all_reduce(value, op=dist.ReduceOp.SUM)
        torch.cuda.synchronize()
        actual = value.item()
        expected = dist.get_world_size()
        assert actual == expected, f'Expected {expected}, got {actual}'
        print(f'rank={dist.get_rank()} sum={actual} expected={expected}', flush=True)
    finally:
        dist.destroy_process_group()


if __name__ == '__main__':
    main()
