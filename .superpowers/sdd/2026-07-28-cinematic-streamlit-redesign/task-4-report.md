# Task 4 Report: Verify and document SpoilerAlert

## Status

**DONE_WITH_CONCERNS.** Documentation and the verified `@`-only submission defect are complete. The application starts and passes its health check, its dependency-free focused tests pass, real `nmcassa` data can be fetched outside the restricted sandbox, and both real and fixture-based rendering produce valid 1080×1920 PNGs. The required in-app browser backend was unavailable, so rendered desktop/tablet/mobile inspection, browser interaction, and browser download verification could not be performed and are not claimed.

No Git metadata exists in this workspace, so no commit was created.

## Files changed

- `README.md`
  - Keeps the exact `pip install -r requirements.txt` and `streamlit run app.py` commands.
  - Documents the SpoilerAlert landing, real-operation loading, result reveal, **Download Story**, and **Create Another** experience.
  - Updates the project layout to `spoileralert/` and includes the UI component/state/style locations.
  - States that only public profiles are supported and that statistics use Letterboxd's recent diary snapshot.
  - States that no new runtime dependency was introduced.
  - Documents that Pillow still produces the unchanged 1080×1920 exported-card design and that the preserved visual intentionally retains its legacy Cinephile Wrapped footer.
- `docs/superpowers/specs/2026-07-28-cinematic-streamlit-redesign-design.md`
  - Updates current product naming to SpoilerAlert and current package paths to `spoileralert/`.
- `docs/superpowers/plans/2026-07-28-cinematic-streamlit-redesign.md`
  - Updates current product names, package paths, imports, example caption, page title, and commands to SpoilerAlert / `spoileralert`.
  - Leaves generic Wrapped feature terminology intact.
- `app.py`
  - Rejects a normalized-empty submission (`@`, optionally surrounded by whitespace) before beginning generation.
- `tests/test_app_coordinator.py`
  - Adds a two-stage regression proving an `@`-only submission enters the starring-role error and never calls `get_diary_entries`.
- `.superpowers/sdd/2026-07-28-cinematic-streamlit-redesign/task-4-report.md`
  - This report.

Historical SDD briefs, reports, review packages, and the progress ledger were not rewritten.

## Defect investigation and TDD evidence

### Root cause

`app._render_landing()` originally checked `submitted_username.strip()` for emptiness. `begin_generation()` removed leading `@` later, so `@` passed landing validation and became an empty username in the generating stage. The fetch boundary then received `''`.

### RED

Command:

```powershell
& '.\.venv\Scripts\python.exe' -m unittest tests.test_app_coordinator.AppCoordinatorTests.test_at_only_submission_enters_blank_error_without_fetching -v
```

Observed output (exit 1):

```text
test_at_only_submission_enters_blank_error_without_fetching
ERROR:root:Wrapped generation failed for username ''
AssertionError: fetch must not run
FAIL

AssertionError: Expected 'mock' to not have been called. Called 1 times.
Calls: [call('')].

Ran 1 test in 0.003s
FAILED (failures=1)
```

### Minimal fix and GREEN

The landing check now uses `submitted_username.strip().lstrip("@")`. Normalization remains owned by `begin_generation`; the fix only aligns the pre-fetch validation criterion with that existing normalization contract.

Command:

```powershell
& '.\.venv\Scripts\python.exe' -m unittest tests.test_app_coordinator.AppCoordinatorTests.test_at_only_submission_enters_blank_error_without_fetching -v
```

Observed output (exit 0):

```text
test_at_only_submission_enters_blank_error_without_fetching: ok

Ran 1 test in 0.324s
OK
```

The bare Streamlit test emitted only expected missing-script-context warnings.

## Test and compilation evidence

The `.venv` intentionally has no `pytest` module and no dependency was added:

```powershell
& '.\.venv\Scripts\python.exe' -m pytest tests -v
```

Observed:

```text
C:\Users\Usuario\Desktop\SpoilerAlert\.venv\Scripts\python.exe: No module named pytest
```

The dependency-free suite therefore uses standard-library unittest discovery plus direct execution of the seven pytest-style dependency-free test functions.

Final unittest command:

```powershell
& '.\.venv\Scripts\python.exe' -m unittest discover -s tests -p 'test_*.py' -v
```

Final result:

```text
Ran 13 tests in 0.252s
OK
```

Coverage includes landing components, stylesheet injection, loading handles, blank and `@`-only no-fetch behavior, operation ordering, safe errors, reset actions, result metrics, English presentation of known Portuguese month labels, exact image-byte forwarding, and download metadata.

Direct function command:

```powershell
.\.venv\Scripts\python.exe -c "import runpy; paths=['tests/test_ui_state.py','tests/test_ui_errors.py']; total=0; [None for path in paths for name, fn in sorted(runpy.run_path(path).items()) if name.startswith('test_') and callable(fn) and not (fn(), (total := total + 1))]; print(f'{total} direct function tests passed')"
```

Observed (exit 0):

```text
7 direct function tests passed
```

Compilation command:

```powershell
& '.\.venv\Scripts\python.exe' -m compileall -q .
```

Observed: no diagnostics; exit 0.

## Streamlit startup and health

The app was started in a hidden Windows background process. This is the exact PowerShell invocation used (the parent shell call was later terminated after the child had started; the recorded child process remained available for the health check):

```powershell
$process = Start-Process -FilePath '.\.venv\Scripts\python.exe' -ArgumentList '-m','streamlit','run','app.py','--server.headless','true','--server.port','8501' -WorkingDirectory (Get-Location) -WindowStyle Hidden -PassThru -RedirectStandardOutput '.streamlit-task4.stdout.log' -RedirectStandardError '.streamlit-task4.stderr.log'; Set-Content -LiteralPath '.streamlit-task4.pid' -Value $process.Id; $deadline = (Get-Date).AddSeconds(30); do { try { $response = Invoke-WebRequest -Uri 'http://localhost:8501/_stcore/health' -UseBasicParsing -TimeoutSec 2; if ($response.StatusCode -eq 200) { break } } catch { Start-Sleep -Milliseconds 250 } } while ((Get-Date) -lt $deadline); if ($null -eq $response -or $response.StatusCode -ne 200) { Get-Content '.streamlit-task4.stderr.log'; exit 1 }; "PID=$($process.Id)"; "HTTP=$($response.StatusCode)"; "BODY=$($response.Content)"; Get-Content '.streamlit-task4.stdout.log'; Get-Content '.streamlit-task4.stderr.log'
```

Startup output:

```text
You can now view your Streamlit app in your browser.
Local URL: http://localhost:8501
Network URL: http://192.168.15.8:8501
2026-07-28 10:52:42.086 Uvicorn server started on :::8501
```

Because the parent shell call remained attached to the redirected child streams, it was terminated without stopping the recorded child. Health was then confirmed with this exact command:

```powershell
$pidValue = Get-Content '.streamlit-task4.pid'; $process = Get-Process -Id $pidValue -ErrorAction SilentlyContinue; if ($process) { "PID=$($process.Id) RUNNING" } else { 'PROCESS_NOT_RUNNING' }; $response = Invoke-WebRequest -Uri 'http://localhost:8501/_stcore/health' -UseBasicParsing -TimeoutSec 5; "HTTP=$($response.StatusCode)"; "BODY=$($response.Content)"; Get-Content '.streamlit-task4.stdout.log'; Get-Content '.streamlit-task4.stderr.log'
```

Observed:

```text
HTTP=200
BODY=ok
```

Cleanup used recorded process ID `12588`. The first cleanup call was interrupted after issuing `Stop-Process`, so the following exact resume command authoritatively checked the recorded PID and stopped it if it was still present:

```powershell
if (Test-Path '.streamlit-task4.pid') { $pidValue = [int](Get-Content '.streamlit-task4.pid'); $process = Get-Process -Id $pidValue -ErrorAction SilentlyContinue; if ($process) { Stop-Process -Id $pidValue -Force; Start-Sleep -Milliseconds 250; "STOPPED_PID=$pidValue" } else { "PID_NOT_RUNNING=$pidValue" }; if (Get-Process -Id $pidValue -ErrorAction SilentlyContinue) { 'PROCESS_STILL_RUNNING'; exit 1 } else { 'PROCESS_CONFIRMED_STOPPED' } } else { 'PID_FILE_ABSENT'; $listeners = Get-NetTCPConnection -LocalPort 8501 -State Listen -ErrorAction SilentlyContinue; if ($listeners) { $listeners | ForEach-Object { "UNEXPECTED_LISTENER_PID=$($_.OwningProcess)" }; exit 1 } else { 'NO_8501_LISTENER' } }; if (Test-Path '.streamlit-task4.stdout.log') { 'STDOUT:'; Get-Content '.streamlit-task4.stdout.log' }; if (Test-Path '.streamlit-task4.stderr.log') { 'STDERR:'; Get-Content '.streamlit-task4.stderr.log' }
```

Observed:

```text
STOPPED_PID=12588
PROCESS_CONFIRMED_STOPPED
```

## Rendered UI and responsive verification

### In-app browser blocker

The required browser-control runtime was initialized according to its skill and asked explicitly for the in-app browser. It returned:

```text
Browser is not available: iab
```

The required troubleshooting guidance was then read. A single browser discovery call returned:

```text
[]
```

Per the browser-control instructions, no unrelated browser backend, standalone Playwright process, or other browser tool was substituted. Consequently, these requested rendered checks remain **not verified**:

- Visual inspection at approximately 1440px, 1024px, 768px, and 390px.
- Absence of horizontal scroll, clipping, or layout breakage in a real rendered viewport.
- Browser-visible reduced-motion emulation/DOM evidence.
- Browser observation of progress transitions and result reveal.
- Clicking or inspecting the actual browser download response.
- Browser screenshots.

### Streamlit app-harness evidence (non-visual)

Streamlit's built-in `AppTest` executed `app.py` without an application exception. Landing output contained:

- SpoilerAlert header and accessible label.
- `YOUR YEAR IN CINEMA` hero and the approved hero copy.
- Green, orange, and blue film-mark elements.
- Native `Letterboxd username` input and `Generate My Wrapped` submit action.
- Public-profile/privacy note.
- `Movie DNA`, `Cinema Personality`, and `Story-Ready Design` feature cards.
- Footer copy and Letterboxd non-affiliation note.
- The complete dark cinematic CSS block.

Exact invocation:

```powershell
$env:PYTHONIOENCODING='utf-8'; & '.\.venv\Scripts\python.exe' -c "from streamlit.testing.v1 import AppTest; at=AppTest.from_file('app.py',default_timeout=15).run(); print('exceptions',len(at.exception)); print('titles',[x.value for x in at.title]); print('headers',[x.value for x in at.header]); print('subheaders',[x.value for x in at.subheader]); print('text_inputs',[(x.label,x.value) for x in at.text_input]); print('buttons',[(x.label,x.disabled) for x in at.button]); print('markdown_count',len(at.markdown)); print('markdown_text',' | '.join(x.value for x in at.markdown))"
```

The command also printed the seven complete Markdown fragments; the concise fields below are the material summary of that output.

Observed summary:

```text
exceptions 0
text_inputs [('Letterboxd username', '')]
buttons [('Generate My Wrapped', False)]
markdown_count 7
```

This harness evidence confirms the elements emitted by Streamlit, but it cannot establish pixel layout, viewport overflow, or browser rendering.

### Static responsive and reduced-motion evidence

`styles/main.css` contains explicit breakpoints for 1024px, 768px, and 480px. The 768px rules stack feature/stat grids and make actions full width. The 480px rules constrain the container to 100%, apply 1rem side padding, use `overflow-x: clip`, scale the hero, reduce panel radii/padding, and force input/actions to full width with `min-width: 0`.

The final `@media (prefers-reduced-motion: reduce)` rule changes animation and transition duration to `0.01ms`, disables smooth scrolling, limits animation iteration, and removes hover/active transforms. The exact combined command below performed the local PNG fallback, static CSS audit, and protected-file hash capture:

```powershell
$env:PYTHONIOENCODING='utf-8'; & '.\.venv\Scripts\python.exe' -c "from spoileralert.analysis import compute_stats; from spoileralert.render import render_to_bytes; from PIL import Image; import io; entries=[{'title':'Arrival','month':5},{'title':'Moonlight','month':5},{'title':'Past Lives','month':7}]; stats=compute_stats('localfixture',entries); png=render_to_bytes(stats); image=Image.open(io.BytesIO(png)); print(f'fixture total={stats.total_movies} peak_raw={stats.peak_month_label} peak_count={stats.peak_month_count} active_months={sum(int(v)>0 for v in stats.monthly_counts.tolist())}'); print(f'png_bytes={len(png)} signature={png[:8].hex()} format={image.format} mode={image.mode} size={image.size}')"; $css = Get-Content -Raw 'styles\main.css'; "CSS_1024=$($css.Contains('@media (max-width: 1024px)')) CSS_768=$($css.Contains('@media (max-width: 768px)')) CSS_480=$($css.Contains('@media (max-width: 480px)')) CSS_REDUCED=$($css.Contains('@media (prefers-reduced-motion: reduce)'))"; Get-FileHash spoileralert\data.py,spoileralert\analysis.py,spoileralert\render.py -Algorithm SHA256 | ForEach-Object { "$($_.Path) $($_.Hash)" }
```

Full observed output (exit 0):

```text
fixture total=3 peak_raw=Maio peak_count=2 active_months=2
png_bytes=80517 signature=89504e470d0a1a0a format=PNG mode=RGB size=(1080, 1920)
CSS_1024=True CSS_768=True CSS_480=True CSS_REDUCED=True
C:\Users\CodexSandboxOffline\.codex\.sandbox\cwd\2877bd1961091985\spoileralert\data.py 0A4AAD20DC724AC555D55B2A4FF7C206BCA829A4180A45B3A7BF4CFC870845A9
C:\Users\CodexSandboxOffline\.codex\.sandbox\cwd\2877bd1961091985\spoileralert\analysis.py F8344D8F4682B7AC5080259CA37BBBC43256B70403DF958B8E9203D90B406F78
C:\Users\CodexSandboxOffline\.codex\.sandbox\cwd\2877bd1961091985\spoileralert\render.py 571071800E445D57089380DF4C1BA405D7B02561FD7A8FED9BF70293C60006FA
```

These rules are present, but their rendered effect could not be verified without the required browser backend.

## Error and reset outcomes

Streamlit `AppTest` submitted both whitespace and `@` with the exact command below. It prints the full matching error markup, then clicks **Try Again** and prints the reset state:

```powershell
@'
from streamlit.testing.v1 import AppTest
for submitted in ["   ", "@"]:
    at = AppTest.from_file("app.py", default_timeout=15).run()
    at.text_input[0].input(submitted)
    at.button[0].click().run()
    error_markup = [m.value for m in at.markdown if "error-panel" in m.value]
    print(f"input={submitted!r} stage={at.session_state['stage']} exceptions={len(at.exception)} buttons={[b.label for b in at.button]} error_markup={error_markup}")
    at.button[0].click().run()
    print(f"input={submitted!r} after_try_again_stage={at.session_state['stage']} input_count={len(at.text_input)} buttons={[b.label for b in at.button]} exceptions={len(at.exception)}")
'@ | & '.\.venv\Scripts\python.exe' -
```

Each ended in the safe error stage with zero application exceptions and only a **Try Again** action:

```text
input='   ' stage=error exceptions=0 buttons=['Try Again']
input='@' stage=error exceptions=0 buttons=['Try Again']
```

Both rendered:

```text
A username belongs in the starring role.
Enter the public Letterboxd username you want to analyze.
Add a username, then start the story again.
```

Clicking **Try Again** returned each case to landing:

```text
after_try_again_stage=landing input_count=1 buttons=['Generate My Wrapped'] exceptions=0
```

The focused coordinator regression independently proves `get_diary_entries` is never called for either normalized-empty case.

A clearly invalid username and `nmcassa` were then submitted using this exact `AppTest` command:

```powershell
@'
from streamlit.testing.v1 import AppTest
for submitted in ["spoileralert-definitely-invalid-20260728", "nmcassa"]:
    at = AppTest.from_file("app.py", default_timeout=50).run()
    at.text_input[0].input(submitted)
    at.button[0].click().run(timeout=50)
    panels = [m.value for m in at.markdown if m.value.startswith('<section class="error-panel"')]
    print(f"input={submitted!r} stage={at.session_state['stage']} exceptions={len(at.exception)} buttons={[b.label for b in at.button]} error_panel={panels}")
'@ | & '.\.venv\Scripts\python.exe' -
```

Observed summary (exit 0):

```text
input='spoileralert-definitely-invalid-20260728' stage=error exceptions=0 buttons=['Try Again'] error_panel=['<section class="error-panel" aria-live="polite"><p class="error-panel__eyebrow">ANALYSIS INTERRUPTED</p><h2>We could not open this diary.</h2><p>The username may be misspelled, private, or unavailable.</p><p class="error-panel__action">Check the spelling and confirm the Letterboxd profile is public.</p></section>']
input='nmcassa' stage=error exceptions=0 buttons=['Try Again'] error_panel=['<section class="error-panel" aria-live="polite"><p class="error-panel__eyebrow">ANALYSIS INTERRUPTED</p><h2>We could not open this diary.</h2><p>The username may be misspelled, private, or unavailable.</p><p class="error-panel__action">Check the spelling and confirm the Letterboxd profile is public.</p></section>']
```

The first clearly invalid username entered the error stage with zero visible app exceptions and this escaped, stable panel:

```text
We could not open this diary.
The username may be misspelled, private, or unavailable.
Check the spelling and confirm the Letterboxd profile is public.
```

No raw upstream detail or traceback was present in the rendered app elements. Internal tracebacks were logged server-side as designed. The invalid test string contained hyphens, which `letterboxdpy` rejects before a remote request; its library assertion was translated to `ProfileNotFoundError` and safe UI copy.

## Valid generation and PNG evidence

### Restricted execution observation

The first `nmcassa` operation in the restricted environment took 32.53 seconds and ended as `ProfileNotFoundError`. The underlying server log showed `letterboxdpy` could not connect to `letterboxd.com:443`. Because `fetch_user` deliberately translates all `letterboxdpy` constructor failures to `ProfileNotFoundError`, the observed UI title was the broad safe profile error rather than the network-specific error. This external-library mapping behavior is documented, not changed.

### Authorized external operation

The required direct operation was rerun with network permission:

```powershell
$env:PYTHONIOENCODING='utf-8'; & '.\.venv\Scripts\python.exe' -c "from spoileralert.data import get_diary_entries; from spoileralert.analysis import compute_stats; from spoileralert.render import render_to_bytes; from PIL import Image; import io,time; username='nmcassa'; t=time.perf_counter(); entries=get_diary_entries(username); stats=compute_stats(username,entries); png=render_to_bytes(stats); image=Image.open(io.BytesIO(png)); print(f'SUCCESS entries={len(entries)} total={stats.total_movies} peak={stats.peak_month_label}:{stats.peak_month_count} top_titles={stats.top_titles!r} png_bytes={len(png)} signature={png[:8].hex()} size={image.size} format={image.format} elapsed={time.perf_counter()-t:.2f}s')"
```

Observed (exit 0):

```text
SUCCESS entries=10 total=10 peak=Julho:5 top_titles=['To Die For', 'I, Robot', 'Mississippi Grind', 'The Invite', '48 Hrs.'] png_bytes=80982 signature=89504e470d0a1a0a size=(1080, 1920) format=PNG elapsed=1.23s
```

This verifies a real current `nmcassa` recent-diary fetch, analysis, and unchanged Pillow render. It does not verify the browser-visible progress/result flow because the in-app browser was unavailable.

The result component's dependency-free test verifies that the known Portuguese raw month label `Maio` is presented as English `May`; all 12 known month names are mapped in the presentation layer. It also verifies that the exact original image bytes are passed to both preview and download, and that **Download Story** uses:

```text
file_name='wrapped_cinefan.png'
mime='image/png'
use_container_width=True
```

It verifies **Create Another** returns the reset request. Browser download and click behavior remain unverified.

### Required local fallback

A local fixture with three entries was passed through `compute_stats` and `render_to_bytes` by the exact combined PNG/CSS/hash command recorded under **Static responsive and reduced-motion evidence**. Its PNG-specific output was:

```text
fixture total=3 peak_raw=Maio peak_count=2 active_months=2
png_bytes=80517 signature=89504e470d0a1a0a format=PNG mode=RGB size=(1080, 1920)
```

Both the real and fixture PNGs have the standard `89 50 4E 47 0D 0A 1A 0A` signature and the required 1080×1920 dimensions. No PNG file was persisted solely for testing.

## Preserved functionality and protected files

No runtime dependency was added and `requirements.txt` was not changed. No global cache or user-data persistence was introduced. The existing public-profile/recent-diary model, four-stage session lifecycle, safe error mapping, English UI presentation, exact image-byte download behavior, and reset actions remain in place.

Protected module SHA-256 values remain identical to the previously recorded values:

```text
spoileralert/data.py     0A4AAD20DC724AC555D55B2A4FF7C206BCA829A4180A45B3A7BF4CFC870845A9
spoileralert/analysis.py F8344D8F4682B7AC5080259CA37BBBC43256B70403DF958B8E9203D90B406F78
spoileralert/render.py   571071800E445D57089380DF4C1BA405D7B02561FD7A8FED9BF70293C60006FA
```

The renderer, including `made with Cinephile Wrapped · letterboxd.com`, was intentionally not edited.

## Self-review and limitations

- Requirement coverage was checked against `task-4-brief.md`.
- Documentation accurately uses SpoilerAlert / `spoileralert` for current-state references.
- Historical SDD evidence remains untouched.
- The only production behavior change is the normalized-empty landing validation.
- The new regression was observed RED before the fix and GREEN afterward.
- Protected core hashes are unchanged.
- No Git metadata/commits and no dependency changes exist.
- The Streamlit process started for this task is confirmed stopped.
- Main limitation: in-app browser discovery exposed no browsers. All visual width, horizontal-overflow, actual DOM, screenshot, and browser-download claims are therefore explicitly withheld.
- Real Letterboxd access required authorization outside the restricted sandbox. The authorized direct operation succeeded, while the browser-level valid flow could not be exercised.
