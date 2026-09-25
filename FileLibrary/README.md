# FileLibrary App (File Library & Media Transcoding Module)

## Description
The FileLibrary module serves as the digital file repository for the system, managing unstructured technical documents, instructional videos, images, etc. It provides secure chunked uploading for large files and integrates a background video transcoding pipeline.

## Models
* **FileCategory**: Directory and taxonomy management for files, such as "Video Training", "Technical Drawings", "Backups", etc.
* **LibraryFile**: Stores file title, physical path, size, description, uploader, and dedicated video transcoding state fields (`video_status` / `video_standard` / `video_error`).

## Key Features & Logic
* **Chunked Upload & Resume Capability**:
  * For files larger than 5MB, the frontend chunks the file into 5MB slices for sequential upload with progress tracking and network failure resumption, supporting single file uploads up to 100MB.
* **Background Automated Video Transcoding**:
  * When a video file is uploaded, a background process invokes `ffmpeg` to transcode the video into a standardized, universally compatible **720p / H.264 / MP4** format and updates `video_status` (processing / success / failed).
  * Once transcode completes, users can play training videos directly via the built-in HTML5 player.
* **Granular Access Control**:
  * `admin`: Full administration, deletion, and category management rights.
  * `manager`: File upload capability without deletion rights.
  * `operator`: Browse, stream playback, and download permissions.

## Change Notice
* Transcoding optimization: Enforced `libx264` encoding to resolve compatibility issues where certain mobile devices or Chrome browsers produced audio without video.
