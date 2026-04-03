# Design System Specification: Cyber Ops Intelligence

## 1. Overview & Creative North Star
**Creative North Star: "The Tactical Command Layer"**

This design system moves away from the "flat web" aesthetic and toward a high-fidelity tactical interface. It mimics a mission control center—not through cluttered buttons, but through **Sophisticated Density**. The goal is to make the user feel like an elite operator. We achieve this through intentional asymmetry, where data-heavy "monitors" (cards) are balanced by expansive, dark "voids" (negative space), creating a rhythmic flow that guides the eye to critical threats without visual fatigue.

The system breaks the template look by treating the screen as a **3D light-box**. Elements aren't just placed; they are projected onto the interface.

---

## 2. Colors & Surface Architecture

### The Palette
The core of this system is high-contrast functionalism. We use the deep `surface` tokens to create a sense of infinite depth, allowing our primary "electric" accents to pop as if they were light-emitting diodes (LEDs).

*   **Primary (`#adc6ff`):** Our "Electric Blue" signal. Used for active data states and primary actions.
*   **Secondary (`#4edea3`):** The "Safe" emerald green. Reserved for cleared assets and secure statuses.
*   **Tertiary (`#ffb3ad` / `#ff5451`):** The "Threat" red. Used sparingly to command immediate attention.

### The "No-Line" Rule
**Explicit Instruction:** Do not use 1px solid borders to section off large areas of the UI. 
Traditional boxes create visual "noise" that slows down an operator. Instead, boundaries must be defined by:
1.  **Tonal Shifts:** Placing a `surface-container-low` component against a `surface` background.
2.  **Shadow-Defined Edges:** Using soft, ambient depth to imply a break.

### Surface Hierarchy & Nesting
Treat the interface as a series of stacked tactical panels. Use the following hierarchy for nesting:
*   **Base Layer:** `surface` (#0f131d) — The deep "void" of the command center.
*   **Secondary Sectioning:** `surface-container-low` (#171b26) — For sidebars or navigation rails.
*   **Active Interaction Areas:** `surface-container` (#1c1f2a) — The standard container for content.
*   **Floating Panels/Modals:** `surface-container-high` (#262a35) — To pull the user’s focus forward.

### The "Glass & Gradient" Rule
To achieve the "Cyber Ops" look, main action areas or "Hero" metrics should utilize **Glassmorphism**.
*   **Implementation:** Combine `surface_variant` with a `backdrop-filter: blur(12px)` and a 20% opacity. 
*   **Signature Textures:** For high-level CTAs, apply a subtle linear gradient from `primary` (#adc6ff) to `primary_container` (#4d8eff) at a 135-degree angle. This adds "soul" and dimension to an otherwise cold interface.

---

## 3. Typography
The typography strategy is a juxtaposition between **Editorial Authority** (Space Grotesk) and **Technical Precision** (Inter/JetBrains Mono).

| Level | Token | Font Family | Weight | Purpose |
| :--- | :--- | :--- | :--- | :--- |
| **Display** | `display-lg` | Space Grotesk | 700 | High-level system status or major metrics. |
| **Headline**| `headline-md` | Space Grotesk | 500 | Section titles; creates an "Intel Report" feel. |
| **Title**   | `title-md` | Inter | 600 | Card titles and sub-headings. |
| **Body**    | `body-md` | Inter | 400 | General descriptions and data labels. |
| **Label**   | `label-sm` | JetBrains Mono | 500 | Technical metadata, timestamps, and hex codes. |

*Director’s Note:* Always use `label-sm` (Monospace) for any dynamic data strings or IP addresses to maintain the "hacker-terminal" aesthetic.

---

## 4. Elevation & Depth

### The Layering Principle
Depth is achieved through **Tonal Layering** rather than drop shadows.
*   **Nesting Example:** A `surface-container-lowest` card placed inside a `surface-container-low` section creates a "recessed" look, making the card feel like a modular slot in a physical machine.

### Ambient Shadows
When an element must "float" (like a dropdown or tactical overlay):
*   **Shadow Color:** Use a tinted shadow based on `on_surface` (e.g., `#000000` at 40% opacity).
*   **Blur:** Use extra-diffused values (e.g., `box-shadow: 0 20px 40px rgba(0,0,0,0.4)`).

### The "Ghost Border" Fallback
If a visual divider is required for accessibility, use a **Ghost Border**:
*   Use the `outline_variant` (#424754) at **15% opacity**. This provides a hint of structure without breaking the seamless "glass" aesthetic.

---

## 5. Components

### Buttons (The "Signal" Component)
*   **Primary:** Solid `primary` fill with `on_primary` text. No border. Apply a 2px "outer glow" using `primary` at 30% opacity on `:hover`.
*   **Secondary:** Ghost style. `outline` color for text, with no background. On hover, fill with `primary` at 10% opacity.
*   **Corner Radius:** Stick to the `sm` (0.125rem) or `md` (0.375rem) scale to maintain a sharp, military-grade feel.

### Data-Dense Cards
*   **Construction:** Use `surface-container` with `md` roundedness. 
*   **Constraint:** **Never use horizontal dividers.** Use vertical padding (from the spacing scale) and font-weight shifts to separate content.
*   **Indicator Lights:** Use 4px x 4px circles with a `box-shadow` glow (e.g., `0 0 8px secondary`) to represent live system status.

### Input Fields
*   **Base:** `surface_container_low` background with a `none` border. 
*   **Focus State:** Transition the bottom edge to a 2px `primary` line. This mimics a terminal prompt.

### Additional Tactical Components
*   **The "Log Stream":** A scrolling area using `label-sm` typography and `surface-container-lowest` background. 
*   **The "Status Beacon":** A pulsating `primary` or `tertiary` dot next to critical alerts to draw the operator’s eye without using intrusive popups.

---

## 6. Do’s and Don'ts

### Do:
*   **Do** embrace density. This is a pro-tool; users need to see a lot of data at once.
*   **Do** use "Optical Alignment." Sometimes a monospaced label needs a 1px nudge to feel centered.
*   **Do** use `primary_fixed_dim` for non-interactive text that still needs to feel "high-tech."

### Don't:
*   **Don't** use standard "Web Blue" (#0000FF). Only use the tokens provided.
*   **Don't** use heavy gradients. Use them only on small, critical touchpoints (CTAs).
*   **Don't** use rounded corners (`xl` or `full`) on tactical panels. Keep them `sm` or `md` to maintain a professional, rigid authority.
*   **Don't** use 100% white for text. Use `on_surface_variant` (#c2c6d6) to reduce eye strain in dark environments.