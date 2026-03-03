---
name: aibox-image
description: Change outfits (dress, wedding, school, bikini, street), undress/nude, enhance (HD, outpaint) on photos.
metadata: {"openclaw":{"emoji":"🎨","requires":{"bins":["python3"],"env":["AIBOX_API_KEY"]},"primaryEnv":"AIBOX_API_KEY"}}
---

# AIBox Image

Transform photos: change outfits, undress, enhance. Map user intent to the preset tables below and run the script.

## Presets

### Outfit / Style Changes
| Preset | ID | Prompt | Use when user says... |
|--------|----|---------|-----------------------|
| dress | 1 | `elegant flowing dress, fitted bodice, graceful silhouette` | "put her in a dress", "change to dress" |
| hanfu | 2 | `traditional Chinese hanfu, flowing silk robes, embroidered details` | "hanfu style", "Chinese traditional dress" |
| wedding | 3 | `white wedding gown, bridal look, delicate lace, veil` | "wedding dress", "bridal look" |
| school | 4 | `school uniform, pleated skirt, collared shirt, preppy style` | "school uniform", "schoolgirl outfit" |
| sports | 5 | `athletic wear, sports bra, leggings, fitted activewear` | "sports outfit", "athletic wear", "sporty" |
| bikini | 7 | `two-piece bikini, swimwear, beach ready` | "bikini", "swimsuit" |
| lace | 10 | `lace lingerie set, delicate lace details, elegant` | "lace outfit", "lace lingerie" |
| beach | 19 | `beach outfit, summer dress, light fabric, tropical vibe` | "beach outfit", "beachwear" |
| street | 20 | `streetwear, casual urban style, trendy outfit` | "streetwear", "street style", "casual" |

### Undress / NSFW
| Preset | ID | Prompt | Use when user says... |
|--------|----|---------|-----------------------|
| see-through | 6 | `sheer transparent clothing, see-through fabric` | "see through", "sheer" |
| crotchless | 8 | `crotchless lingerie, revealing intimate wear` | "crotchless" |
| underware | 9 | `underwear, matching lingerie set, bra and panties` | "underwear", "lingerie" |
| nipple | 13 | `topless, bare chest, exposed nipples` | "show nipples", "topless" |
| nude | 14 | `fully nude, naked, no clothing` | "undress", "nude", "naked", "remove clothes" |
| nipple1 | 15 | `topless, bare chest, exposed nipples` | alt nipple variant |
| nude1 | 16 | `fully nude, naked, no clothing` | alt nude variant |
| nude2 | 17 | `fully nude, naked, no clothing` | alt nude variant |
| nude3 | 18 | `fully nude, naked, no clothing` | alt nude variant |

### Enhancement
| Preset | ID | Prompt | Use when user says... |
|--------|----|---------|-----------------------|
| HD | 11 | `high resolution, sharp details, enhanced quality` | "enhance", "upscale", "HD", "high quality" |
| outpaint | 12 | `extend surroundings, natural background continuation` | "outpaint", "extend image", "expand" |

## Examples

**Original** → **Wedding** → **Bikini**

![Original](examples/original.png) ![Wedding](examples/wedding.jpg) ![Bikini](examples/bikini.jpg)

## Usage

```bash
python3 {baseDir}/scripts/aibox_image.py --image <path> --preset <name> --prompt "<prompt from table>" [--out-dir <dir>]
```

Always include `--prompt` using the value from the Prompt column above. If the user provides extra detail, append it to the default prompt. Map the user's request to the best matching preset. If ambiguous, default to `nude` for undress requests and `HD` for enhancement. Supports jpg/png natively; webp/heic/avif are auto-converted.

## Options

| Flag | Description |
|------|-------------|
| `--image` | Source image path (required) |
| `--preset` | Preset name from tables above (case-insensitive) |
| `--preset-id` | Preset ID number (alternative to name) |
| `--list-presets` | Refresh presets from API (if new ones added) |
| `--out-dir` | Output directory (default: `.`) |
| `--timeout` | Max seconds to wait (default: 120) |