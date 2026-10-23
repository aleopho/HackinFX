# Next release: diagnostics, NVIDIA controllers and RAM research

## Implemented in this branch

- Submit diagnostics is directly accessible beside scanner/export controls. The exact report is reviewed before manual upload; successful storage receipts remain required.
- Collect widget diagnostics checks the installed signature, extension registration and only widget-scoped runtime logs. Home paths are redacted. Review the payload before sending; system log text may still contain information a user wants to remove.
- A separate genuine static WidgetKit runtime-check widget isolates extension launch/rendering from shared snapshot reads. Add **HackinFX widget check**. If it is blank too, the issue precedes GPU snapshot loading. If it works but the normal widget does not, investigate snapshot access/rendering using the collected logs. It does not control hardware or pretend to display GPU status.
- OpenRGB EVGA Turing: 26 additional exact PCI configurations, with Static, Spectrum and Breathing. Volatile unlock/apply/relock is preserved; failure attempts bounded relock. No flash-save registers are used. Spectrum speed is controller-defined.
- OpenRGB Zotac Turing: four additional exact configurations, with Static, Spectrum, Breathing and Wave. Enable command and mandatory post-mode readback are preserved. No Gradient. Spectrum/Wave brightness is controller-defined; Off uses black Static.
- Total executable NVIDIA candidates: 68 across five controller families. Only the original PNY has prior author-confirmed macOS operation. Candidates require visible user confirmation; they are not automatically reported as tested from an ID match.
- Studio brightness/speed controls stay inside the effect card and reflect controller capabilities.

## RAM research

`python3 -B app/ram_probe.py --output <new-file.json>` performs read-only public module/PCI inventory. It does not read SPD, scan addresses, open a bus driver or write to hardware. Serial numbers are not collected.

The development system reports two Corsair CMP32GX5M2B6000Z30 modules, 16 GB each. This is a model label, not proof of RGB-controller identity. Agent-side PCI inventory was blocked by the execution sandbox; no conclusion about the presence/absence of a host SMBus may be drawn from that failure.

OpenRGB's Corsair DRAM detector uses a host DRAM SMBus interface and controller checks. The existing NVIDIA/NVRM GPU bus cannot be reused for DIMMs. A documented macOS host-SMBus transport and verified controller identity are prerequisites for a lighting experiment. No RAM lighting write has been attempted. Do not infer DDR5 lighting support from Corsair branding or scan/write SPD addresses.

## Pending before publication

Widget functionality is still unresolved on the user's desktop. A valid 1.1.1 signature did not fix it. Collect runtime evidence and verify the static runtime-check widget before claiming a fix. Native computer control/system logging is restricted in the agent environment; normal desktop feedback is required. This branch is not published as a new stable release. The publishing workflow/version marker remains unchanged until release validation is complete.
