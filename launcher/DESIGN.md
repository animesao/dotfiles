# DESIGN.md — Launcher

## 1. Objective
A search-first app launcher that feels instant and invisible. The user opens it, types, launches, done — under 3 seconds. Visual identity: Gruvbox dark, compact, no wasted pixels. Quality bar: every frame is purposeful; nothing decorative.

## 2. Product Context
- **What it does:** Launch apps via keyboard-first search with an "All" browse fallback.
- **Who it's for:** A Wayland/niri power user who values keyboard workflow over mouse.
- **Adjacent brands (feel like these):** Spotlight (macOS), rofi, wofi
- **Distant brand (do not feel like this):** Windows Start Menu (heavy, mouse-first, animated bloat)
- **Cultural register:** technical, minimal, utilitarian

## 3. Visual Foundations

### 3a. Color
- **Neutral scale:** `--bg: #1d2021, --surface: #282828, --surface-hi: #3c3836, --hover: #504945, --border: #57514e`
- **Text:** `--fg: #ebdbb2, --fg-dim: #a89984, --fg-faint: #7c6f64`
- **Accent:** `--green: #b8bb26` (primary action / selected state)
- **Semantic:** `--yellow: #fabd2f` (secondary), `--aqua: #8ec07c` (info), `--red: #fb4934` (danger)
- **Usage rules:** Green only on active tab and selected item background. Never as decorative fill.

### 3b. Typography
- **Display face:** Adwaita Sans, Bold
- **Body face:** Adwaita Sans, Regular/Medium
- **Fallback stack:** sans-serif
- **Type scale:** 8 / 9 / 11 / 13 px (compact, utility-first)
- **Weight discipline:** Bold for titles and active states only. Regular for body. Medium for app names.

### 3c. Spacing & rhythm
- **Base unit:** 4px
- **Spacing scale:** 2, 4, 6, 8, 10, 12, 14 px
- **Generous whitespace:** Not applicable — this is a compact utility, not a landing page. Every pixel is earned.

### 3d. Component seeds
- **Button (tab pill):** 26px height, rounded-13, icon + label. Active: green fill, dark text. Inactive: transparent, dim text.
- **Card / container:** No cards. Flat list with hover/selected background rectangles, rounded-8.
- **Iconography:** Feather SVGs (stroke-only, 2px weight). System icons via QIcon::fromTheme with fallback letter-circles.
- **Search bar:** Full-width, dark bg, 1px border, rounded-10, magnifying glass icon left, text input right.

## 4. Accessibility
- **Text contrast:** fg-on-surface ≥ 7:1 (Gruvbox AA compliant)
- **Motion:** None — instant show/hide, no animations
- **Focus indicators:** Search field always focused on open. Keyboard nav via ↑/↓.
- **Alt text policy:** N/A — pure utility, no images.

## 5. Voice & Tone
- **Register:** Technical, zero-copy
- **Sentence rhythm:** Short — labels only, no sentences
- **Words this brand uses:** Search, All, Launch
- **Words this brand refuses:** Welcome, Explore, Discover, Seamless
- **Address:** Implicit — the interface speaks through actions, not words

## 6. Implementation Practices
- **Token format:** Python constants (BG, SURFACE, etc.)
- **Component library:** Bespoke PyQt6 widgets
- **Image treatment:** SVG inline icons + system icon theme
- **Grid system:** Single-column list, no formal grid
- **Motion rules:** None — instant state changes

## 7. Anti-Patterns
- **No gradient backgrounds.** Gruvbox is flat; gradients break the aesthetic.
- **No emoji as icons.** Use proper SVGs or system icons; emoji render inconsistently.
- **No animation for show/hide.** The launcher must feel instant — 0ms transition.
- **No decorative elements.** Every pixel serves a function. No badges, ornaments, or filler.
- **No mouse-first design.** Keyboard navigation is primary. Mouse is fallback.

## 8. Decision-Making
1. **Keyboard speed.** If a choice slows keyboard nav, reject it.
2. **Visual density.** Prefer compact over spacious — this is a utility, not a showcase.
3. **Gruvbox fidelity.** All colors from the palette; no custom hues.
4. **Zero dependencies.** Only PyQt6 + system libs. No npm, no web views.
5. **Instant feedback.** Search filtering must be synchronous, no debounce.

## 9. Workflow
1. Parse .desktop files on startup (cached in memory)
2. Show empty search bar on open — no apps visible until user types or clicks "All"
3. Filter synchronously on each keystroke
4. ↑/↓ to navigate, Enter to launch, Tab to toggle mode, Esc to close
5. Launch app via subprocess.Popen with start_new_session=True
6. Hide immediately on launch — no confirmation, no delay
