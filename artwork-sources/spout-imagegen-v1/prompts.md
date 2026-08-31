# GPT Image 2 sprite-sheet prompts

Mode: Host-Native (`image_gen`, Codex subscription). Each phase is generated in a separate call and then processed by `scripts/build-whale-spout.py`.

## Shared art direction

Create one square black-and-white 4×4 sprite sheet containing exactly sixteen independently composed animation cels in row-major order. Invisible conceptual seams: no grid, gutters, dividers, borders, labels, text, numbers, or watermark. Every cel has a pure white background and one thin gently wavy horizontal waterline at exactly 34% of that cel's height. Pure flat vector ink only: #000000 and #ffffff, crisp edges, no gray, colour, gradient, shadow, texture, or lighting.

Keep the same unmistakable DeepSeek-whale morphology in every cel, facing right: large rounded head at the right end, thick crescent torso, one small white circular eye, one large clean white crescent belly/mouth cutout, and exactly two compact tail flukes at the left end. No generic smiling whale, realistic whale, orca, fish, extra fins, extra eyes, pupils, teeth, or anatomy drift. Constant scale and identity.

This is native character animation, not a rigid logo transform. Every adjacent cel must redraw the body: a coherent travelling S-bend passes through the thick torso, the belly arc compresses and extends, and the two tail flukes counter-kick continuously. Head motion stays controlled while the spine, abdomen, tail stock, and flukes visibly deform. No duplicate poses, teleports, sudden rotations, scale jumps, clipping, merged cels, or motion blur. Keep every mark inside its own cel with blank safety margins.

## Phase 1 — rise to surface

Cell 1 starts fully underwater below the fixed waterline in a calm horizontal launch posture, head right and tail left. Across sixteen small monotonic advances, the whale swims upward and slightly right until cell 16 rests naturally at the waterline with the upper head and back above it. No spout yet. The torso performs one clear S-wave and the tail counter-kicks through all sixteen cels. Preserve constant scale and gradual angle change from about -12 degrees to 0 degrees.

## Phase 2 — body flex and spout growth

Cell 1 continues directly from phase 1 cell 16 at the waterline. The whale remains surface-bound while its torso visibly inhales, arches, compresses, and relaxes; the tail stock and two flukes continue a small counter-kick. A tiny blowhole puff begins around cell 4, becomes a short two-prong spray, then grows gradually into an elegant medium three-stream V-shaped fountain by cell 16. Use only thin black curves and a few small droplets. The whale must not become rigid while the spray changes.

## Phase 3 — peak spray and falling droplets

Cell 1 continues directly from phase 2 cell 16 with a medium fountain. The torso reaches a gentle arch and the tail counters it. The fountain grows to its tallest airy three-stream peak around cells 5–7, then breaks naturally into separated droplets that arc outward and fall. By cell 16 the main jets are gone but several droplets remain descending. Keep a visible travelling body bend and tail follow-through in every adjacent cel; no static pasted whale under changing water.

## Phase 4 — settle and return underwater

Cell 1 continues from phase 3 cell 16. Remaining droplets fall and disappear by cell 4. The whale exhales, settles, dips beneath the fixed waterline, and swims downward-left through a smooth S-curve. The torso and belly extend while the tail delivers a final counter-kick. Cell 16 must be extremely close to phase 1 cell 1 in position, scale, orientation, body bend, and waterline so the new surface act closes seamlessly. No spray after cell 4.
