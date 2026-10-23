# ABI and implementation sources

Reviewed on 2026-10-23. `probe.py` is a new Python implementation, not a copied NullMoth/Mesa shim. RM structures and constants are based on NVIDIA's MIT-licensed public SDK definitions; retain NOTICE.txt with the tool.

## NullMoth bridge (pinned v2.5.3)

- [NVRM.cpp](https://github.com/nullmoth/nvidia-macos-driver/blob/v2.5.3/kexts/NVRM/NVRM.cpp): `externalMethod` dispatch index 1 = sEsc; input scalar = escape number; variable input/output structure. Unhandled escapes pass to `rm_ioctl`. User-client types 0 and 1 represent control/device connections. No selector 0 call is made by this tool.
- [Mesa adaptation](https://github.com/nullmoth/nvidia-macos-driver/blob/v2.5.3/nvk/nvk-macos.patch): `nvRmApiAlloc`, `nvRmApiControl`, `nvRmApiFree` demonstrate NVOS21/54/00 and the root/device/subdevice object sequence. This establishes a candidate transport; it does not prove GPU I2C support.

## NVIDIA headers (pinned 610.57.04)

Paths below are relative to [NVIDIA/open-gpu-kernel-modules at 610.57.04](https://github.com/NVIDIA/open-gpu-kernel-modules/tree/610.57.04).

| Path | Definition used |
| --- | --- |
| `src/common/sdk/nvidia/inc/nvos.h` | NVOS21: 32 bytes, pointer at 16; NVOS54: 32 bytes, pointer at 16; NVOS00: 16 bytes; NV01_ROOT_CLIENT = 0x41 |
| `src/nvidia/arch/nvalloc/unix/include/nv_escape.h` | RM_FREE = 0x29, RM_CONTROL = 0x2A, RM_ALLOC = 0x2B |
| `src/common/sdk/nvidia/inc/class/cl0080.h` | NV01_DEVICE_0 = 0x80; NV0080_ALLOC_PARAMETERS: 56 bytes, vaSpaceSize at 24 |
| `src/common/sdk/nvidia/inc/class/cl2080.h` | NV20_SUBDEVICE_0 = 0x2080; subDeviceId: uint32 |
| `src/common/sdk/nvidia/inc/class/cl402c.h` | NV40_I2C = 0x402C |
| `src/common/sdk/nvidia/inc/ctrl/ctrl0000/ctrl0000gpu.h` | GET_ATTACHED_IDS = 0x201, 32 uint32 IDs, unused IDs 0xFFFFFFFF; GET_ID_INFO_V2 = 0x205, 32-byte struct |
| `src/common/sdk/nvidia/inc/ctrl/ctrl402c.h` | GET_PORT_INFO = 0x402C0101, 16 one-byte port flags |

The ABI checks reject incompatible local structure sizes/alignment. They do not establish compatibility with every future driver. NVIDIA's I2C port indices are returned without assigning the PNY controller to any index.

## Device identity

[OpenRGB PCI constants](https://gitlab.com/CalcProgrammer1/OpenRGB/-/blob/master/pci_ids/pci_ids.h) identify NVIDIA as 0x10DE, RTX 4080 as 0x2704, and PNY subsystem vendor as 0x196E. The probe records the subsystem device ID rather than assuming a VERTO revision. It performs no RGB transaction even on a matching card.

## Current validation status

The transport has been exercised on the development Mac; exact supported PNY RGB behavior is described in docs/COMPATIBILITY.md at the repository root. Offline/native/network validation and remaining interactive checks are listed in docs/DEVELOPMENT.md. The pinned source references above describe the implementation basis, not compatibility with every driver version or card.
