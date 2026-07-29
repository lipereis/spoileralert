# SpoilerAlert Cinematic Streamlit Redesign

## Objective

Transform the existing Streamlit interface into a polished, responsive cinematic product while preserving the application's data fetching, analytics, Pillow rendering, and PNG download behavior. The interface will be English-only for this iteration. The exported 1080x1920 PNG will retain its current visual design.

## Scope

This redesign covers the Streamlit website presentation and UI state management. It may add small presentation helpers, focused UI components, a dedicated stylesheet, and Streamlit theme configuration. It will not replace Streamlit, add a headless browser, redesign the exported image, or change the meaning of existing analytics.

## Architecture

`app.py` remains the Streamlit entry point and coordinates the page stages. Presentation is split into small functions under `components/`, while shared styling lives in `styles/main.css`. The existing modules keep their responsibilities:

- `spoileralert/data.py`: fetch and normalize public Letterboxd diary data.
- `spoileralert/analysis.py`: calculate existing Wrapped statistics.
- `spoileralert/render.py`: generate the existing 1080x1920 PNG.

The UI uses per-session Streamlit state with four explicit stages:

- `landing`: header, hero, username form, trust note, benefits, and footer.
- `generating`: visually stable progress feedback tied to real operations.
- `result`: editorial result reveal, statistics, PNG preview, download, and reset.
- `error`: contextual error content and a retry path.

Generated statistics and PNG bytes are stored only in the active Streamlit session so normal reruns do not repeat fetching or rendering. No global cache stores user-specific results. The “Create Another” action clears only the relevant UI state and returns to `landing`.

## User Flow

1. The visitor sees a minimal header, editorial hero, and focused generator panel.
2. The visitor enters a public Letterboxd username and submits the form.
3. Empty input is rejected immediately with accessible inline feedback.
4. A stable analysis state reports actual fetching, analysis, and rendering steps without artificial delays.
5. Success transitions to a dedicated result view with the unchanged generated PNG.
6. The visitor can download the PNG or reset the experience to create another.
7. Failures transition to a helpful error state with a clear next action.

## Visual System

The interface uses a charcoal base and CSS variables based on the approved palette:

- Background: `#0b0d0f`
- Surface: `#111418`
- Elevated surface: `#171b20`
- Primary text: `#f5f7f8`
- Secondary text: `#9aa3ad`
- Letterboxd green: `#00e054`
- Letterboxd orange: `#ff8000`
- Letterboxd blue: `#40bcf4`
- Low-opacity white borders for resting and hover states

The centered content width is approximately 1100–1200px. Static radial accents provide restrained green, blue, and orange atmosphere without moving backgrounds. Cards use subtle borders, controlled shadows, and 16–28px corner radii. Blur and glow remain limited.

Existing local Poppins fonts are loaded with `@font-face`; robust system sans-serif fallbacks cover missing assets. Headings use responsive `clamp()` sizing, strong negative letter spacing, and generous whitespace.

## Landing Experience

The transparent or lightly elevated header contains the SpoilerAlert wordmark and “Your year in cinema” label. No large navigation menu is added.

The hero uses the approved English content:

- Eyebrow: “YOUR YEAR IN CINEMA”
- Heading: “Discover the story behind your movie taste.”
- Supporting copy: “Turn your Letterboxd diary into a personal, cinematic and shareable visual experience.”

Three restrained colored marks reference Letterboxd's green, orange, and blue identity.

The generator panel includes a visible label, concise public-profile explanation, a username input at least 54px tall, and the “Generate My Wrapped” primary action. The privacy note states that only public Letterboxd profile information is analyzed and that data is not permanently stored, matching the current in-memory implementation.

Below the form, three equal-height numbered cards explain Movie DNA, Cinema Personality, and Story-Ready Design using the supplied copy. Before generation, these sections remain visible as the product's value proposition.

## Loading Experience

The generating view uses stable Streamlit status and progress primitives with customized presentation. Messages map to real work:

1. Opening the public Letterboxd diary.
2. Finding patterns in the available diary activity.
3. Rendering the cinematic story image.

No fake waits are introduced. Form submission and stage state prevent accidental duplicate execution during ordinary reruns.

## Result Experience

The result view opens with:

- Eyebrow: “THE FINAL CUT”
- Heading: “This was @username's recent chapter in cinema.”
- Supporting copy: “A story told through movies, months and memories.”

The username is rendered through Streamlit text APIs or escaped before any HTML interpolation.

The unchanged PNG appears fully visible inside a responsive poster-like frame. It is not presented as a generic device mockup. Summary cards show only safely derived existing information:

- Total films
- Peak month
- Films watched during the peak month
- Number of months with represented diary activity

The primary “Download Story” action uses the existing PNG bytes. The secondary “Create Another” action safely resets the current session's generated state.

## Error Handling

User-facing errors never expose raw exceptions or stack traces. Each contains a title, short explanation, and suggested next action.

- Empty username: ask for a Letterboxd username.
- Missing or private profile: ask the user to check spelling and confirm the profile is public.
- No recent diary activity: explain that recent public diary entries are needed.
- Network failure: explain that Letterboxd could not be reached and suggest retrying.
- Parsing or unexpected failure: provide a safe general message and retry option.

Because the third-party library groups several profile failures under broad exceptions, private and nonexistent profiles may share one helpful message unless a reliable distinction is available.

## Interaction and Accessibility

Interactions use 160–300ms transitions and 500–800ms entrance animations with `cubic-bezier(0.22, 1, 0.36, 1)`. Motion is limited to subtle fade/slide entrances, hover elevation, input focus feedback, button press feedback, progress transitions, and the result reveal.

`prefers-reduced-motion: reduce` disables or minimizes nonessential animation. Controls retain visible keyboard focus, labels remain accessible, errors include text and not color alone, heading structure is logical, and important information is never hover-only. Text contrast targets WCAG AA for ordinary content.

## Responsive Behavior

The layout is intended to support 1440px, 1024px, 768px, and 390px widths. At smaller widths, the responsive rules scale headings down, stack columns, reduce card padding, make the input and actions span the available width, retain side margins, and constrain the story preview to its container. Rendered verification at these widths remains unavailable in the current environment because the required in-app browser backend could not be discovered; these behaviors are supported by the implemented CSS but are not represented as visually verified.

## Streamlit Integration

`.streamlit/config.toml` sets the matching dark theme. `st.set_page_config` uses a wide layout and collapsed sidebar. Stable, minimal Streamlit selectors customize native widgets where wrapping content in semantic classes is insufficient. Fragile generated class names are avoided.

The application will continue to use native Streamlit inputs, forms, status, progress, image, and download components. Custom HTML is limited to presentation fragments owned by the application, and untrusted username input is never injected unescaped.

## Verification

Completion requires:

- `python -m compileall .`
- Focused automated checks for new state and error helpers where practical
- Successful local Streamlit startup
- Landing-page and interaction inspection in a browser
- Desktop and 390px mobile layout checks
- Empty and invalid username checks
- Valid public-profile generation when network access and Letterboxd availability permit
- PNG preview and download verification

If external network access prevents a live profile test, that limitation will be reported explicitly rather than represented as verified.

## Dependencies and Compatibility

No new dependency is planned. The design remains compatible with Streamlit Cloud and uses the existing local Poppins assets. Missing font assets degrade to system fonts in the website, while existing Pillow rendering behavior remains unchanged.

## Known Framework Limitations

Streamlit controls its own widget markup and rerun model. Styling therefore relies on a small number of documented or stable `data-testid` selectors, and stage transitions occur through Streamlit reruns rather than client-side route animations. These constraints will be handled conservatively to preserve reliability.
