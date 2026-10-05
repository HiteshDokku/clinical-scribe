# Frontend Design Direction: Chart and Signature
**Reference:** ADR-0010

## 1. Visual Language & Tokens
This is a clinical tool. The aesthetic is physical, material, and readable. NO dark slate, NO glassmorphism, NO neon/cyberpunk accents, and NO generic SaaS dashboard templates.

**Color Palette:**
*   `--paper`: `#FAFAFA` (App background)
*   `--paper-2`: `#FFFFFF` (Card/Surface background, elevated with subtle shadow)
*   `--text-primary`: `#1C1917` (High contrast for readability)
*   `--text-secondary`: `#57534E`
*   `--speaker-clinician`: `#3E5C6B` (Used for UI chips and speaker identification)
*   `--speaker-patient`: `#5E6B3E` (Used for UI chips and speaker identification)
*   `--draft`: `#FCD34D` (Used strictly for `insufficient_content` / "Not discussed" states)
*   `--alert`: `#EF4444` (Used for red-flag tier items and high-risk interactions)

## 2. Typography Rule (Strict)
*   **UI Elements & Headers:** *Hanken Grotesk* (Clean, legible sans-serif for buttons, labels, and navigation).
*   **Clinical Data & Transcripts:** *JetBrains Mono* (Used for all verbatim transcript text, timestamps, and raw clinical data output). Verbatim speech is ALWAYS mono.

## 3. Layout: The Stepped Deck
*   **Transcripts:** Left-aligned, single-column rows. NEVER use chat-bubble layouts.
*   **Review Flow:** A stepped-card review layout with discrete per-statement progress segments. It is a sequence of distinct decisions (Diagnosis -> Medications -> Sign), not an endless scrollable feed.

## 4. Motion as a Safety Signal
*   Animation must use Framer Motion (or equivalent spring-physics).
*   Motion is deliberate, not decorative. Every animation answers a clinician's action (e.g., sliding a confirmed card away) with exactly one deliberate flourish reserved for the final "Sign-unlock" moment. 
