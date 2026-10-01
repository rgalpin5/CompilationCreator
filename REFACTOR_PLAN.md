# CompCreator refactor plan

This plan splits the largest modules into single-responsibility files. It does not change product behavior, the HTTP contract, the on-disk job layout, or the desktop packaging entry points. No application code moves until a phase below is explicitly started.

The current tree already has routers, services, and UI components. The problem is not a missing `services/` folder. A handful of files each own several jobs, so a change to cookies, trimming, or the export screen has to be made inside a module that also does unrelated work.

## What is too large

Line counts are the current source files, not generated output.

| File | Lines | What it actually owns |
| --- | --- | --- |
| `frontend/components/ClipPlayer.tsx` | 617 | YouTube IFrame API loader, player lifecycle, playhead polling, intro and outro buttons, drag trim bar, keyboard nudge |
| `backend/app/services/ytdlp_service.py` | 494 | URL normalization, channel paging, format selection, cookie and Deno setup, two download strategies, an ffmpeg trim, duration probe |
| `frontend/app/page.tsx` | 413 | Channel feed, timeline edits, cut-step navigation, job polling, save, and the editor/logs switch |
| `backend/app/services/ffmpeg_service.py` | 370 | Stream probe, layout voting, per-clip encode, 4K fit, concat demuxer, concat-filter fallback |
| `frontend/components/LogsPanel.tsx` | 274 | Fetch, search, sort, two tables, view-count and date formatting |
| `backend/app/services/compiler.py` | 223 | Timeline checks, parallel download, prep, three-step concat fallback, usage recording |
| `frontend/components/ExportBar.tsx` | 185 | 4K checkbox, cancel confirmation, job status, save-folder field |
| `frontend/lib/api.ts` | 158 | Every response type and every endpoint |
| `backend/app/desktop.py` | 165 | OS paths, browser detection, PATH and cookie env, static mount, Uvicorn, pywebview |
| `backend/app/services/runner.py` | 139 | Cancellation tokens, process groups, Windows and POSIX kill |
| `backend/app/services/usage_store.py` | 130 | JSON load, per-video counts, compilation names, log queries |
| `backend/app/services/delivery.py` | 97 | Save path rules and the copy-then-delete handoff |

Smaller files (`timeparse.py`, `job_store.py`, `models.py`, `ChannelForm.tsx`, `Timeline.tsx`, `CutStep.tsx`, `VideoGrid.tsx`) are already close to one job. Leave them alone until a split forces a type to move.

## Rules for every phase

- Behavior stays the same. Public HTTP paths, status strings, progress text, env var names, and the desktop log path do not change.
- Move code before rewriting it. A phase is a file split plus import updates, not a new download strategy or a new UI.
- Keep a compatibility import at the old path until the next phase deletes it. Tests currently import `ytdlp_service`, `ffmpeg_service`, `compiler`, and `usage_store` directly.
- One phase lands on its own. Do not split the frontend and the backend in the same change.
- After each phase, run `PYTHONPATH=. python -m unittest discover -s tests` from `backend/`. From `frontend/`, run `npm test` (Vitest) for the pure helpers. The cut player, feed paging, and export poll have no automated tests yet and still need a manual pass described in that phase.
- Do not add a framework, a state library, or a repository layer. FastAPI, Pydantic, and React state are enough.
- Do not wire the stubs in `backend/app/stubs/`. They stay comments until a feature is actually built.
- Do not rename the Python package `app`. Packaging and `vercel.json` both load `app.main:app`.

## Target layout

New packages, not a rewrite of `main.py`. Routers stay thin. They validate, call one function, and map errors to HTTP.

```text
backend/app/
  main.py                         unchanged role: CORS, routers, store startup
  config.py
  timeparse.py
  models.py                       split only if a later phase needs it
  routers/
    channels.py
    compilations.py
    usage.py
    deps.py                       replaces module-level store globals
  youtube/
    urls.py                       normalize_channel_url and video-page detection
    listing.py                    list_channel_videos
    cookies.py                    cookie file, browser name, Deno path
    formats.py                    format selector
    download.py                   section vs full-file decision and download
    client.py                     YoutubeDL options and the download call
  media/
    probe.py                      ffprobe layout and duration
    plan.py                       prep_plan, fit_4k, Prep, StreamLayout
    encode.py                     finalize_clip, normalize_clip
    concat.py                     concat_clips, concat_reencode
    process.py                    shared argv runner that raises FfmpegError
  compilation/
    validate.py                   validate_timeline
    pipeline.py                   run_compilation
  jobs/
    store.py                      JobStore
    runner.py                     Runner and JobCancelled
  usage/
    store.py                      UsageStore
  delivery.py                     stays one module; it is already focused
  desktop/
    paths.py
    browser.py
    server.py                     Uvicorn plus static mount
    __init__.py                   main() used by packaging/entry.py
  services/                       temporary re-exports, deleted in the last phase
  stubs/                          untouched
```

```text
frontend/
  app/page.tsx                    view switch only
  features/
    channel/
      ChannelForm.tsx
      VideoGrid.tsx
      VideoCard.tsx
      LazyThumbnail.tsx
      useChannelFeed.ts
    timeline/
      Timeline.tsx
      types.ts                    TimelineClip
      useTimeline.ts              add, remove, move, active index
    cuts/
      CutStep.tsx
      ClipList.tsx
    player/
      ClipPlayer.tsx              composition only
      youtube-api.ts              script loader and YT types
      useYouTubePlayer.ts         cue, poll, seek, trusted duration
      TrimBar.tsx
      TrimControls.tsx            intro and outro button rows
    export/
      ExportBar.tsx
      JobStatusCard.tsx
      useDownloadFolder.ts
      useExportJob.ts             create, poll, cancel, save
    logs/
      LogsPanel.tsx
      VideoTable.tsx
      CompilationTable.tsx
      format.ts                   views and timestamps
  lib/
    api/
      client.ts                   fetch wrapper and API_BASE
      types.ts
      channels.ts
      compilations.ts
      usage.ts
    time.ts                       stays; it is already one concern
```

`components/ui/` stays where shadcn put it. `components.json` aliases do not need a new `hooks` folder; feature hooks live next to the feature that uses them.

## Phase 1 — Pure YouTube and media splits

**Why first.** `ytdlp_service.py` and `ffmpeg_service.py` are the backend monoliths, and the existing tests already call their functions. Splitting them is the highest-value move with the smallest product risk.

**`ytdlp_service.py` becomes the `youtube/` package.**

| New module | Functions that move |
| --- | --- |
| `youtube/urls.py` | `_is_video_id`, `_video_page_url`, `_uploader_channel_url`, `normalize_channel_url` |
| `youtube/listing.py` | `list_channel_videos`, `_thumbnail` |
| `youtube/cookies.py` | `_with_cookies`, `_with_challenge_solver`, `_deno_path`, `_executable`, `_browser_name`, `_cookiefile` |
| `youtube/formats.py` | `_format_selector`, `max_video_height` |
| `youtube/download.py` | `use_concurrent_download`, `download_section`, `_download_with_sections`, `_download_full_then_trim`, `_find_download` |
| `youtube/client.py` | `_ytdlp_options`, `_run_ytdlp`, `_watch_url` |

`_probe_duration` does not belong next to yt-dlp. Move it to `media/probe.py` and call it from the full-file trim path. The trim argv in `_download_full_then_trim` can stay in `download.py` for this phase so the download decision and the trim stay in one place. A later phase can share argv builders with `media/encode.py` only if both sides still emit the same command.

Leave `max_video_height` in `formats.py` and do not delete it in this phase. It is unused, and deleting it is a separate, obvious change once imports have settled.

**`ffmpeg_service.py` becomes the `media/` package.**

| New module | Functions that move |
| --- | --- |
| `media/probe.py` | `probe_layout`, `StreamLayout`, `_probe_duration` |
| `media/plan.py` | `layouts_match`, `prep_plan`, `fit_4k`, `Prep`, picture and audio keys, `_fps_bucket` |
| `media/encode.py` | `finalize_clip`, `normalize_clip`, `_scale`, `_audio_encoder` |
| `media/concat.py` | `concat_clips`, `concat_reencode` |
| `media/process.py` | `FfmpegError`, `_run` |

`compiler.py` keeps calling the same operations. Point it at the new modules. Also keep `app.services.ytdlp_service` and `app.services.ffmpeg_service` as re-export modules so `tests/test_channel_list.py`, `tests/test_timeparse.py`, `tests/test_stream_copy.py`, and `tests/test_cookies.py` do not have to change in the same commit. Update those imports in the commit that deletes the shims.

**Done when**

- `unittest discover` passes with the old import paths.
- A channel load, a one-clip export, cancel, and save still work against a short video you have the right to use.
- No router file changed except import lines, if any.

## Phase 2 — Compilation pipeline and job runner

**Why second.** `compiler.py` is the orchestration layer. It should not know ffmpeg argv details, and it should not own timeline parsing. After phase 1 the imports are long; this phase shortens the orchestrator instead of moving ffmpeg again.

Move:

- `validate_timeline` and `videos_missing_4k` to `compilation/validate.py`. `videos_missing_4k` is only referenced from tests today. Keep it.
- `run_compilation` and `_run_parallel` to `compilation/pipeline.py`.
- `JobStore` to `jobs/store.py`.
- `Runner`, `JobCancelled`, and the process-kill helpers to `jobs/runner.py`.

`pipeline.py` should read as the status machine: download, probe, plan, prepare, concat, record usage, or cancel. The three concat attempts (copy, normalize-then-copy, re-encode) stay in this function until a later change. Extracting them into a new policy object would be a behavior risk with no caller that needs the split.

`UsageStore` moves to `usage/store.py` with `_blank_video` and `_compilation_name` in the same file. One hundred and thirty lines of one persistence type does not need a second module.

Routers import the new locations. `app.services.compiler`, `job_store`, `runner`, and `usage_store` remain as re-exports for one phase.

**Done when**

- `test_cancel.py`, `test_usage.py`, `test_delivery.py`, and the timeline tests pass.
- Cancel during download still kills the ffmpeg or yt-dlp child. That path lives in `jobs/runner.py` and is easy to break by dropping `start_new_session` or the Windows process-group flag.
- Progress strings are unchanged. The UI matches on status values, and the progress sentences are user-visible.

## Phase 3 — Store injection

**Why after the moves.** `channels.py`, `compilations.py`, `usage.py`, and `main.py` share state through `init_usage` and `init_store` writing module globals. That works for one process. It makes tests order-dependent and makes a second app instance in the same interpreter unsafe.

Replace the globals with FastAPI dependencies in `routers/deps.py`:

- `get_job_store()` and `get_usage_store()` read objects stored on `app.state` during startup.
- Routers take those dependencies instead of reading `store` and `usage` from the module.
- `create_compilation` still schedules `run_compilation` with the store instances it already resolved. Do not look the stores up again inside the background task from a global.

Do this only after phase 2, so the dependency module imports the final store locations.

**Done when**

- The module globals and `init_*` functions are gone.
- `/health`, channel list, usage, and a compilation create/status/cancel/save cycle still work.
- Tests that construct `UsageStore(path)` or `JobStore(path)` directly are unchanged.

## Phase 4 — Desktop package

`desktop.py` is smaller than the media stack, but it mixes four reasons to change: where files live, which browser is installed, how the API is served, and how the window opens.

| New module | Responsibility |
| --- | --- |
| `desktop/paths.py` | `app_support_dir`, `bundle_dirs`, `static_dir` |
| `desktop/browser.py` | `detect_browser` |
| `desktop/server.py` | `prepare_environment`, `mount_ui`, free port, wait for `/health` |
| `desktop/__init__.py` | `main` and `_run` |

`packaging/entry.py` imports `app.desktop.main`. Keep that path working by exporting `main` from `app/desktop/__init__.py` and deleting `app/desktop.py` in the same change. A module and a package cannot share the name `desktop`.

**Done when**

- `python packaging/entry.py` still starts against a built `frontend/out`, or the import of `main` succeeds in a unit check if a window cannot be opened in CI.
- Application Support paths and the browser order are unchanged.

## Phase 5 — Frontend state out of the page

`app/page.tsx` is the UI monolith. It owns the channel feed, the timeline, and the export job, then passes twenty props into `CutStep` and `ExportBar`. Split state by the thing it remembers, not by the component that happens to render it.

| Hook | State and functions that move out of `page.tsx` |
| --- | --- |
| `useChannelFeed` | `videos`, loading flags, `hasMore`, errors, `feedRef`, `loadVideos`, `loadMore`, and the usage-count refresh that runs when a job becomes `ready` |
| `useTimeline` | `clips`, `activeIndex`, `addVideo`, `updateClip`, `removeClip`, `moveClip`, `adjustAfterRemove` |
| `useExportJob` | `job`, `submitting`, `savingDownload`, `jobActive`, `busy`, poll effect, `cancelExport`, `downloadExport`, `exportCompilation` |

`page.tsx` keeps `stage` (`pick` or `cuts`) and `view` (`editor` or `logs`). Those two values decide which screen is mounted. `openCuts` stays beside `stage` because it only validates and switches screens.

`TimelineClip` moves from `Timeline.tsx` to `features/timeline/types.ts`. `CutStep`, `ExportBar`, and the page all import it today, and the type is not a timeline-widget detail.

`lib/api.ts` splits in the same phase so the new hooks do not import a 158-line barrel for one function:

- `lib/api/client.ts` — `API_BASE` and `request`.
- `lib/api/types.ts` — `Video`, `Job`, `Logs`, and the payload types.
- `lib/api/channels.ts`, `compilations.ts`, `usage.ts` — one file per router.

Keep `lib/api.ts` as a re-export until every component import has moved. The `@/lib/api` imports in `VideoGrid`, `ExportBar`, `CutStep`, and `LogsPanel` can switch in this phase because they are type-only or single-function imports.

**Done when**

- Loading a channel, loading a second page, toggling a video, reordering, opening the cut step, exporting, cancelling, and saving all behave as they do now.
- Switching to Logs and back does not reset the timeline. Today both views stay mounted and are hidden with CSS. Preserve that. Unmounting Logs on each switch is fine because it refetches; unmounting the editor is not, because the timeline is only in React state.
- The poll still waits two seconds, still ignores a stale response after the effect cleans up, and still refreshes compilation counts when status becomes `ready`.

## Phase 6 — Clip player

Do this after phase 5 so the player split is not mixed with the page-state move.

`ClipPlayer.tsx` has three independent pieces:

1. **IFrame API.** `youtube-api.ts` holds the `YT` types, the script tag, and `loadYouTubeApi`. The promise cache stays module-level. One page should still load the script once.
2. **Player session.** `useYouTubePlayer.ts` holds the refs (`playerRef`, `loadedIdRef`, `trustedIdRef`, `switchedAtRef`, `lastDurationRef`), the ready and failure flags, cue-on-id-change, the 250 ms poll, `rememberTiming`, `seek`, and `readPlayhead`. The duration-trust logic is the fragile part: after a video change, the hook ignores a duration that still matches the previous video for 1.5 seconds. Move that block verbatim. Do not simplify it in the same change.
3. **Trim chrome.** `TrimBar.tsx` is the pointer and keyboard control. `TrimControls.tsx` is the intro and outro button groups, including the “use full video” action. `ClipPlayer.tsx` composes the card, the iframe fallback, the meter text, and these two children.

`setTrimPoint`, `parseTime`, and `formatSeconds` stay in `lib/time.ts`. The player already depends on them; do not copy the math into the component folder.

**Done when**

- Cutting an intro, cutting an outro, skipping, dragging both handles, arrow-key nudge, and “use full video” still update the clip.
- Changing video with Previous and Next does not apply the previous video’s duration to the new trim.
- If the IFrame API fails to load, the plain embed iframe still appears.
- Export from the cut step still sends the edited `start` and `end`.

## Phase 7 — Logs, export bar, and video grid

These are smaller and can land as one frontend change or three, in any order.

- `LogsPanel.tsx`: move `formatViews` and `formatWhen` to `features/logs/format.ts`. Move each table, including its search and sort state, into `VideoTable.tsx` and `CompilationTable.tsx`. The parent fetches once when `active` is true and passes the arrays down. Keep the fetch in the parent so both tables share one request and one error.
- `ExportBar.tsx`: move the status block and the save-folder field into `JobStatusCard.tsx`. Move the `localStorage` key and the `fetchDownloadFolder` effect into `useDownloadFolder.ts`. The 4K checkbox and the cancel confirmation can stay in `ExportBar.tsx`.
- `VideoGrid.tsx`: move `LazyThumbnail` to its own file. Optionally move the selected-card markup to `VideoCard.tsx`. The intersection observer that calls `onLoadMore` stays in the grid.

`CutStep.tsx` is 152 lines and mostly layout. Extract the clip list (the intro and outro summary buttons) to `ClipList.tsx` only if phase 6 makes the file a pass-through. Otherwise leave it.

**Done when**

- Logs search and both sort modes still work, including the green badge on the highest use count.
- The save folder still restores from `localStorage` key `compcreator-download-folder`, and a blank value still means Downloads.
- Infinite scroll still loads the next page and still offers Try again after an error.

## Phase 8 — Remove the shims

After phases 1–4, delete `backend/app/services/` re-export modules once every import points at `youtube`, `media`, `compilation`, `jobs`, or `usage`. Delete `frontend/lib/api.ts` once every import points at `lib/api/`.

Run the full unittest module and the manual UI pass from phases 5–7 one more time. Update `README.md` layout section so it matches the tree. Do not update `PLAN.md`; that file is the original build plan and is historical.

## What not to refactor

- **Concat fallback order** in `run_compilation`. Copy, then normalize-and-copy, then filter re-encode is the production behavior. A cleaner pipeline that always normalizes would change file size and runtime.
- **Cookie resolution order.** File path, then inline cookies, then browser. Desktop depends on the browser step being skipped when a cookie file is set.
- **Job folder names** (`raw_###`, `part_###`, `norm_###`, `compilation.mp4`, `concat.txt`). Delivery and cancel delete the whole job directory, but log messages and half-written exports are easier to recognize with the current names.
- **Hidden editor/logs panes.** Switching views must not drop unsaved timeline state.
- **shadcn `components/ui/`.** Regenerating them is unrelated to the monoliths.
- **Stubs.** Moving them into the new packages would suggest they are live.
- **`packaging/build.py`.** It is a script with one `main`. Splitting the ffmpeg download from the PyInstaller command is optional and is not required to make the app modular.

## Suggested order of work

1. Phase 1, backend media and YouTube, with shims.
2. Phase 2, pipeline and stores, with shims.
3. Phase 3, dependencies instead of globals.
4. Phase 5, page hooks and API client. This unblocks the UI without waiting on desktop.
5. Phase 6, player.
6. Phase 7, logs, export bar, grid.
7. Phase 4, desktop, whenever a desktop build is convenient. It does not block the UI work.
8. Phase 8, delete shims and refresh the README layout.

Each numbered phase should be reviewable on its own. If a phase cannot keep the existing tests green without editing assertions, stop and treat that as a behavior change, not as part of the split.
