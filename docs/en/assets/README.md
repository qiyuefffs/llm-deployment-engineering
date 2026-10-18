# Knowledge base diagrams and sample assets

[简体中文](../../01-deployment-foundations/assets/README.md) | **English**

[Knowledge base home](../README.md)

## 1. Framework diagram

The English homepage uses the [English framework diagram](framework.svg), which follows the five capability layers of the source framework.

The original [Chinese framework image](../../01-deployment-foundations/assets/edge-llm-deployment-framework-original.png) is preserved at 1536 × 1024 pixels.

SHA256: `3a4f599b7d7fd71cbf286153c891eb7c8dfb72a55cf25e17da69afc4fedd7f80`.

Use the original to compare the author's workflow, layers, and modules. Read the explanations of GGUF, quantization, device memory, parallelism, and metrics alongside the [technical corrections](../appendices/references.md). Temporary signed image URLs are not retained.

## 2. Public vision sample

The shared [vision-input directory](../../01-deployment-foundations/assets/vision-input) contains the [PNG sample](../../01-deployment-foundations/assets/vision-input/vision-card.png) and its [expected content and SHA256](../../01-deployment-foundations/assets/vision-input/expected.json). See the [generator](../../01-deployment-foundations/examples/make_vision_input.py) and [vision request client](../../01-deployment-foundations/examples/vision_client.py).

## 3. Evidence for engineering examples

Commands, measurements, and transcribed tables from the technical notes are collected in the [evidence directory](../evidence/README.md). Original screenshots without permission for public distribution are excluded. No simulated execution screenshots have been created.

Framework diagrams describe relationships between concepts. Historical measurements retain their sources and test conditions. Standalone case screenshots and project artifacts remain in their own directories.
