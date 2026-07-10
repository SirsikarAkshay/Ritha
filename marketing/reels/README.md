# Ritha demo reels

Self-contained, self-playing product demo reels for Ritha — each is a single
`.html` file with **no build step and no external assets** (all CSS/JS/graphics
inlined, garments drawn as inline SVG flat-lays). Open one in a browser and it
loops on its own.

They're built for social (**9:16** vertical reels) and the website (**16:9**
landing cuts). Every reel carries a light **sustainability** thread (borrow /
rewear / buy-less / CO₂-saved).

## Record one to MP4

There's no video file here — these are HTML animations. To export:

1. Open the `.html` in a browser, full-screen it.
2. Screen-record just the phone frame (macOS: **⌘⇧5** → *Record Selected Portion*).
3. Let it play one loop; trim and export.

Start from **`reel-gallery.html`** — a one-page index that links to every reel.

## The library

`reel-gallery.html` is the index. Each reel is also published as a live Artifact
(links below) for quick sharing.

### Travel demos — origin → destination
| File | Format | What it shows | Live |
|---|---|---|---|
| `reel-bengaluru-tokyo.html` | 9:16 | Mild-climate closet → Tokyo's cold; **what to buy** | [▶](https://claude.ai/code/artifact/d1593eaf-5a67-4726-8849-b11606698443) |
| `reel-bengaluru-tokyo-16x9.html` | 16:9 | The same story as a landing-page hero | [▶](https://claude.ai/code/artifact/58b9d5b1-a784-4f90-99d2-a18c18e217bb) |
| `reel-southindia-japan.html` | 9:16 | Tropical wardrobe adapts to a cool Japanese spring | [▶](https://claude.ai/code/artifact/05ad4f03-8122-4bf2-8707-d13ece6fee82) |
| `reel-japan-3day.html` | 9:16 | 3-day Tokyo carry-on: packing, dress code, places | [▶](https://claude.ai/code/artifact/a8f2ca46-57e9-44fb-b0b5-7373bf51e7f1) |

### Feature & persona demos
| File | Format | What it shows | Live |
|---|---|---|---|
| `reel-onboarding-region.html` | 9:16 | Region starter wardrobe in 60s; N-India vs S-India | [▶](https://claude.ai/code/artifact/5b5534b1-17dc-47b4-860f-da6eab9b1c32) |
| `reel-london-bali.html` | 9:16 | Cold→warm + Balinese temple dress code (sarong) | [▶](https://claude.ai/code/artifact/bc98a10a-b181-4918-824d-2105f02267c6) |
| `reel-family-shared.html` | 9:16 | Shared wardrobe: pack four people, share essentials | [▶](https://claude.ai/code/artifact/83e707df-0574-4719-be4e-eab7d5274e3a) |
| `reel-snap-to-add.html` | 9:16 | Photograph a garment → AI auto-tags it | [▶](https://claude.ai/code/artifact/44f68109-9792-468d-ad9a-64579d323fe0) |
| `reel-chat.html` | 9:16 | Real-time chat in the shared closet: borrow, coordinate | [▶](https://claude.ai/code/artifact/15c319c4-1479-4072-8bf5-ab8599f9c973) |
| `reel-chat-16x9.html` | 16:9 | The chat story as a landing-page hero | [▶](https://claude.ai/code/artifact/5d2b21da-9fb3-431e-929c-8b7d9d5ad9f9) |

**10 pieces** — 8 vertical reels + 2 landing cuts — plus the gallery index.

## Notes

- **Illustrations, not photos.** Garments are hand-authored SVG flat-lays (correct
  colours, product-shot styling), matching the in-app category illustrations. Real
  photographs would need a licensed image set (see `backend/wardrobe/seed_images/`).
- **Accessibility:** each reel has clickable scene dots, a replay button, keyboard
  focus states, and honours `prefers-reduced-motion`.
- Every feature shown maps to a real capability: region starter packs, bag-capacity
  packing, cultural advisor, tap-a-place outfits, shared wardrobes, image
  classification, and 1:1 messaging.
