// Names the UI uses for the API's shapes. The shapes themselves are generated
// from the backend's OpenAPI schema into schema.gen.ts; run
// `./setup.sh api-types` after changing a backend model.
import type { components } from "./schema.gen";

type Schemas = components["schemas"];

export type Video = Schemas["VideoItem"];
export type ChannelPage = Schemas["ChannelResponse"];
export type ClipPayload = Schemas["Clip"];
export type VideoLog = Schemas["UsageVideo"];
export type CompilationLog = Schemas["CompilationEntry"];
export type Logs = Schemas["UsageLogs"];
/** An export job. ``file_url`` is set on hosted deploys, where the browser downloads the MP4 itself. */
export type Job = Schemas["JobStatus"];
export type JobStatus = Job["status"];
