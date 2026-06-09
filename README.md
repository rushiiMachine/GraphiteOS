# GraphiteOS

These are my personalized, rooted & modded GrapheneOS OTA patch scripts
for modifying the OS with a locked bootloader.

This project is derived from chenxiaolong's [my-avbroot-setup] template and has been adapted to my needs,
as well as schnatterer's [rooted-graphene] project for its documentation.

## Requirements

* Host must run Linux **or** an Android device must be connected via `adb`
    * Needed for running a statically-linked Android executable
* python3
* [uv](https://github.com/chenxiaolong/my-avbroot-setup/) (Python package manager)

All other binary tools (`avbroot`, `afsr`, `custota-tool`) will be downloaded at runtime.

## Usage

Install the required Python dependencies. `uv` will create a venv to install them into.

```bash
uv sync
```

Then, generate signing keys to resign patched OTAs:

```bash
uv run graphite.py keys
```

Make sure to create a backup of the keys placed in `.keys` on a separate medium. If lost,
installing new OTAs will become impossible without unlocking your bootloader (and losing
all your data in the process).

Then, run the patch script:

```bash
uv run graphite.py \
  --input $OTA_ZIP \
  --verify-public-key-avb verify_avb_pkmd.bin \
  --verify-cert-ota verify_ota.crt \
  [--magisk[=topjohnwu,pixincreate,$APK]] \
  [--magisk-preinit-device=$DEVICE] \
  [--module-alterinstaller[=$ZIP]] \
  [--module-bcr[=$ZIP]] \
  [--module-bootanimation[=$ZIP]] \
  [--module-custota[=$ZIP]] \
  [--module-msd[=$ZIP]]
  [--module-oemunlockonboot[=$ZIP]] \
  [--module-twemoji[=$FONT]] \
  [--debug-shell]
```

This will:

1. Download the necessary binary tools, modules, and other files, and verify their signatures/hash when applicable.
2. Verify the original OTA signatures against the specified verification keys. This includes the
   OTA signature, the `payload.bin` signature, and the signatures of every AVB-enabled partition image.
3. Extract the necessary partition images. This is all done in userspace. Root access is not
   needed as nothing is ever mounted by the host kernel.
4. Copy module files into extracted images and add system init scripts for module `service.sh` and `post-fs-data.sh`.
5. Repack modified partitions, re-signing them with the specified AVB key if necessary.
6. If specified, patch the boot image to inject Magisk.
7. Resign other partitions needed to reestablish AVB's chain of trust, and resign the final patched OTA.
8. Generate the metadata needed to install the OTA using Custota.

## Resources

For information on how to install the patched OTAs and prepare your device, consult the following projects:

- [avbroot]
- [my-avbroot-setup]
- [rooted-graphene]

If you're compiling GrapheneOS from source, these patches may be of interest:

- https://github.com/chenxiaolong/grapheneos-patches
- https://github.com/pixincreate/PixeneOS
- https://github.com/cawilliamson/rooted-graphene/tree/main

## License

This repo is licensed under GPL-3.0-only. Please see [`LICENSE`](./LICENSE) for the full license text.


[avbroot]: https://github.com/chenxiaolong/avbroot

[my-avbroot-setup]: https://github.com/chenxiaolong/my-avbroot-setup

[rooted-graphene]: https://github.com/schnatterer/rooted-graphene
