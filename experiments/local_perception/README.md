# Local Perception Experiment

## Objective

This experimental branch investigates whether the remote VLM-based
perception pipeline in CognitiveOps could be replaced or complemented by
faster local perception models.

The experiment started from the validated `v0.2-structured-perception`
architecture.

The primary motivation was latency: remote multimodal perception requires
several seconds per inference, which is significantly slower than desirable
for reactive autonomous navigation.

## Models evaluated

### FastSeg

FastSeg achieved approximately 46–53 ms inference latency using CPU/OpenVINO.

However, its Cityscapes training domain was too strongly oriented toward
urban environments for reliable rover operation in off-road environments.

### OFFSEG

OFFSEG provided better off-road semantics and achieved approximately 66 ms
inference latency using PyTorch CPU.

Evaluation on real rover imagery still showed important limitations,
including false free/blocked regions, coarse boundaries, and missed small
obstacles.

### SwiftNet / RELLIS and GA-Nav

These approaches were investigated as potential candidates, but directly
usable pretrained checkpoints were not identified during the experiment.

They remain candidates for future investigation.

### GOOSE PP-LiteSeg

The most promising local segmentation candidate was GOOSE PP-LiteSeg.

The official `ppliteseg_category_512.pth` checkpoint was evaluated and
identified as the SuperGradients `pp_lite_b_seg` architecture with:

- 12 semantic classes
- 12,233,792 parameters
- 67.21% reported mIoU

The checkpoint loaded successfully using `strict=True`:

`<All keys matched successfully>`

The official GOOSE preprocessing pipeline was reproduced:

`RGB -> center square crop -> resize 512x512 -> ToTensor()`

No additional normalization was applied.

On real CognitiveOps rover images, the model produced coherent segmentation
of large environmental regions such as ground, vegetation, sky, and
structures.

CPU PyTorch inference at 512x512 produced approximately:

- minimum: 133 ms
- mean: 148 ms
- median: 139 ms
- maximum: 203 ms
- approximately 6.8 FPS

ONNX/OpenVINO optimization of this model was not performed.

## Engineering conclusion

The experiment demonstrated that local semantic segmentation can operate
orders of magnitude faster than the current remote VLM perception pipeline.

However, semantic segmentation and VLM-based perception are not functionally
equivalent.

The VLM provides a richer environmental interpretation, including
traversability reasoning, relevant obstacle identification, approximate
spatial relationships, and navigation context.

Recovering comparable information from a conventional perception stack would
likely require additional components such as monocular depth estimation,
geometry processing, obstacle extraction, traversability rules, and sensor
fusion.

This would introduce substantial perception-specific engineering while not
necessarily reproducing the semantic reasoning capabilities of the VLM.

## Decision

CognitiveOps currently prioritizes cognitive architecture research and
perceptual richness over strict real-time performance.

Remote VLM latency is therefore accepted as a known temporary limitation,
not as a desired architectural property.

Local perception optimization is paused at this point.

Future work may revisit:

- optimized local VLMs
- local LLMs
- ONNX/OpenVINO acceleration
- dedicated inference hardware
- quantization
- hybrid segmentation / depth / VLM architectures

The `experiment/local-perception` branch is retained as an experimental
laboratory and reference.

It is not merged into the main development branch at this stage.

The validated `v0.2-structured-perception` tag remains the stable
architectural checkpoint, while active CognitiveOps development continues
on `feature/l3-l4-gnc`.
