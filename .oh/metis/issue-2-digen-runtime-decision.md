# DIGen 1.1.0 runtime decision

**Date:** 2026-08-12

**Decision hat:** experiment lead

**Issue:** #2

**Status:** assumed for the spike and verified

## Review-trigger investigation

The plan's tooling risk appeared during preflight: the unchanged 2015 DIGen/PDGF distribution did not run directly on the current development runtime.

Evidence collected:

- `DIGen.jar -v` identifies version 1.1.0.
- Java 17 fails because bundled PDGF casts the application class loader to `URLClassLoader`, a pre-Java-9 assumption.
- Java 8 runs DIGen, but `java -jar pdgf.jar` does not discover `pdgf/plugins/tpc-di.jar` on the verified Apple Silicon runtime.
- Running the same bundled PDGF and plugin jars on an explicit classpath completes generation.
- A Java-home launch shim lets the unchanged DIGen entry point create that child JVM. DIGen then completes, writes its report, and reports 4,579,717 rows at scale factor 3.
- The four selected output files are byte-identical between the explicit-classpath diagnostic run and the completed DIGen run.
- DIGen, PDGF, and TPC-DI plugin SHA-256 values match across four independently published copies of the 1.1.0 tool distribution.
- The evaluated copy was staged from `mwiewior/tbd-tpc-di` commit `892927064ab9246340f8b22910081372cd2520b9`; the TPC registration URL remains the canonical acquisition source.

## Choices considered

1. Stop because the 2014 launcher mechanics are incompatible with the current JVM.
2. Modify DIGen, PDGF, or their configuration. This conflicts with the governing requirement to use DIGen unchanged.
3. Substitute hand-authored files. This violates the workload-fidelity guardrail.
4. Keep every official tool byte unchanged and adapt only child-JVM launch mechanics.

## Assumed decision and justification

Under the experiment-lead hat, choose option 4 and continue the spike.

The compatibility shim is environment mechanics, not generator or business policy: it verifies the original jars, invokes DIGen's original main entry point and documented arguments, exposes DIGen's bundled plugin to its bundled PDGF, and retains DIGen's own report. No generated source row is added, removed, rewritten, or inferred. A deterministic cross-path byte comparison provides direct evidence that the shim does not change the selected raw output.

This retires the current reproducibility risk for the bounded slice. It does not authorize modification of DIGen, broaden workload claims, or weaken the publication/fair-use review.
