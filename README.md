# Open Duck Mini v2

[English](README.md) | [简体中文](README_zh.md)

## BREAKING CHANGE: Forge 2.x / Dora 1.x migration

This migration from Forge 1.x / Dora 0.4.x requires coordinated deployment. Align the Forge packages, Dora CLI/coordinator/daemon, this node and its peer nodes before connecting a dataflow; replacing only one node in a Forge 1.x deployment is unsupported. Rebuild and redeploy executable artifacts with the matching environment. Keep `stable/1.x` for deployments that still use the previous stack.

The validated Python baseline is `forge-msgs==2.1.0`, `Pillow==13.0.0`, `forge-common==2.1.0`, the applicable `forge-robot` / `forge-policy` / `forge-kinematics` / `forge-tool` packages at `2.0.0`, and `dora-rs==1.0.1`. Respect this repository's Python and SDK platform requirements. Forge package families have independent versions. Rust nodes retain the published `forge_msgs` crate `2.0.0` with Dora `1.0.1`; Python Msgs `2.1.0` does not require a nonexistent Rust `2.1.0` release. The `forge_msgs.v1` message namespace remains unchanged.

This notice describes the deployment break from the previous stack; it does not declare hardware, real-model or sustained-run acceptance complete. See [this round's verification report](migration/msgs-2.1.0-report.json) for actual tests and outstanding gates.

Forge/Dora robot nodes, pinned Open Duck assets, simulation examples and a Raspberry Pi hardware connection.

## Runtime and configuration

Assets derive from `apirrone/Open_Duck_Mini` at the revision recorded in `assets/asset_manifest.json`. Use `assets/mjcf/open_duck_fixed.xml`, `assets/meshes/open_duck_mini_v2/` and `assets/urdf/robot.urdf`. The fixed-base model checks joints and dataflow; it does not demonstrate balance or walking. No GLB/USD is supplied.

The Forge layer uses 14 joints in radians, ordered as five left-leg, four neck/head and five right-leg joints. `src/robots_open_duck/config.py` defines names, motor IDs, HOME and working limits. SDK angles use the Pi calibration offsets. Sparse position commands retain unspecified joint targets; nonzero velocity, effort and kp/kd are unsupported.

Construction does not touch hardware. `connect()` reads state without homing or enabling motion. Set `enable_action: true` explicitly for actions. `stop()` latches until reconnect. Basic-motion examples return through feedback-confirmed HOME and release enabled torque at completion. Edit `config/config.yaml` for the actual SSH target, Python, runtime and calibration files; use system SSH authentication.

```bash
uv sync
uv run robots-open-duck --help
uv run robots-open-duck watch-state --config config/config.yaml
./examples/03_workflows/real_basic_motion/run_demo.sh --check
./examples/03_workflows/simulation/mujoco_open_duck/run_demo.sh
```

See [hardware motion](examples/03_workflows/real_basic_motion/README.md), [node interface](src/robots_open_duck/README.md) and [robot description](description.md). Running `run_demo.sh` without `--check` performs physical motion and requires support and an explicitly enabled configuration. Build the executable with `scripts/build_pyinstaller.sh`.

## Optional walking integration

The external `move-open-duck` skill and its ONNX/runtime implementation are not distributed here. Configure its installed profile and non-interactive SSH before `paos skill start move-open-duck -p open_duck_real`; stop with `paos skill stop move-open-duck`. It provides six qualitative direction commands, each lasting 10 seconds, not distance/angle control. Cancellation sends zero velocity. Do not run it with the basic-motion workflow; support the robot during startup and prepare free space for walking.

See the [simulation checklist](examples/03_workflows/simulation/JOINT_SWEEP_CHECKLIST.md) and [hardware checklist](examples/03_workflows/real_basic_motion/JOINT_SWEEP_CHECKLIST.md) for historical evidence. Later configuration/interface changes need their own regression; this release-workflow change adds no hardware acceptance. Preserve [licenses](LICENSE) and `assets/README.md` notices.

## Entrypoints

- `robots-open-duck`: `robots_open_duck.main:main`.
- `robots_open_duck`: `robots_open_duck.main:main`.
- `robots-open-duck-rl`: `robots_open_duck.rl_main:main`.

Use each entrypoint's `--help` to inspect its options. Review the supplied configurations and robot limits before enabling hardware. Existing assets, workflow examples, calibration and device setup details are preserved in the [Chinese guide](README_zh.md) and repository documentation.

## Versioned releases

**Mandatory tag-first release rule:** merge the version/lock change, create an annotated version tag on that reviewed commit, build that exact tag, validate the artifacts, then publish. Moving branch names, untagged commit IDs and replacement of published tags are not release inputs.

| Release line | Source | Node/package version | Runtime |
| --- | --- | --- | --- |
| Forge 1.x | `stable/1.x` | `1.x`, tag `v1.X.Y` | Forge 1.x / Dora 0.4.x |
| Forge 2.x | `master` | `2.x`, tag `v2.X.Y` | Forge 2.x / Dora 1.x |

**Legacy normalization:** nodes previously at 0.x on `stable/1.x` release as **1.0.0**, retaining Forge 1.x / Dora 0.4.x dependencies and runtime behavior. Existing 1.x package versions are retained. Node/package majors now follow the Forge compatibility line; a 0.x tag is rejected.

The default branch uses Forge 2.x / Dora 1.x; Forge 1.x / Dora 0.4.x is maintained on `stable/1.x`.

Run **Build versioned release** from `master` for either line. First merge the version/lock changes into the selected source branch, then create an unused **annotated** tag on that reviewed commit. The tag must match package metadata. Never move existing tags or reuse a published version. Dispatch uses the workflow's reviewed tooling with the exact tagged source, so legacy tags need not contain the new release helper.

```bash
# Replace with an existing, reviewed and unpublished tag matching source metadata.
TAG=v1.X.Y
gh workflow run release.yml --ref master -f release_line=1.x -f tag="$TAG"
TAG=v2.X.Y
gh workflow run release.yml --ref master -f release_line=2.x -f tag="$TAG"
```

The workflow verifies tag type, source commit, branch ancestry, source version and locked Forge/Dora compatibility. It builds source archives and wheel/sdist where supported, checks Python distribution metadata and SHA-256, and creates or attaches to a **draft GitHub Release**. Published releases/assets are not overwritten; review all build results and acceptance evidence before publishing. This workflow does not publish node packages to PyPI.

This repository currently releases Python wheel/sdist (when its root project has a build backend) and a source archive. It has no Ubuntu binary workflow; standalone binaries require a separate validated build path.

The source archive preserves the tagged tree; external SDKs/submodules, model downloads and site configuration remain separate prerequisites. A dependency or SDK build failure is not successful release acceptance. Build success does not establish single-node or Gateway-chain `dora run`, hardware, real-model, sustained-run or rollback acceptance. Every acceptance chain must include `adapter-forge-gateway` from the same compatibility line. Forge 2.x is a **breaking change**: align Forge libraries, node versions and Dora across the entire deployment; keep 1.x on its maintenance branch.

## Forge 2.x migration

This branch prepares node version `2.0.0` for Dora 1.x, frozen to Dora `1.0.1` for migration validation. It uses the official Forge 2.x distributions; Common is at least `2.1.0`. Regenerated locks and all executable entrypoints are part of the change.

Every change report must list repository, changes and test evidence, including per-node `dora run` records and a chained test containing `adapter-forge-gateway`. Unavailable hardware/model checks remain pending. Source PRs do not publish stable releases or synchronize GitLab; synchronization follows full acceptance.

## Platform-specific tests

The Pi bridge targets Linux and uses /proc for process ownership checks. Its subprocess integration tests run on Linux CI; portable tests run on other platforms without connecting to hardware.
