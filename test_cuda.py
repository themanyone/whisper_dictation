#!/usr/bin/python3.10
## test.py
##
## Test torch, cuda, cudnn, onnxruntime-gpu
##
## Copyright 2023 Henry Kroll <nospam@thenerdshow.com>
## 
## This program is free software; you can redistribute it and/or modify
## it under the terms of the GNU General Public License as published by
## the Free Software Foundation; either version 2 of the License, or
## (at your option) any later version.
## 
## This program is distributed in the hope that it will be useful,
## but WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
## GNU General Public License for more details.
## 
## You should have received a copy of the GNU General Public License
## along with this program; if not, write to the Free Software
## Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
## MA 02110-1301, USA.
## 

import torch
import onnxruntime as ort

def test_cuda():
    if torch.cuda.is_available():
        print("CUDA is available")
        print("Device: ", torch.cuda.get_device_name())
        print("PyTorch CUDA version:", torch.version.cuda)
    else:
        print("CUDA is not available")
        print()

def test_ort():
    providers = ort.get_available_providers()
    print("Onnxruntime:")
    for p in providers:
        print('\t',p)
    if ort.get_device() == 'GPU':
        print("ONNX Runtime is using GPU")
        print("CUDA version:", ort.cuda_version)
        if torch.cuda.is_available():
            print("cuDNN version:", torch.backends.cudnn.version())
    else:
        print("ONNX Runtime is not using GPU")

if __name__ == '__main__':
    test_cuda()
    test_ort()

