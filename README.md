# Photo-Dump

Photo-Dump is a utility-first photo management platform for photographers who need a simpler way to move images from dedicated cameras into a modern, cloud-backed library.

Live site: https://photo-dump-theta.vercel.app

## What It Does

Photo-Dump lets users create an account, upload images, organize them into albums, browse their library, and download originals. The product is intentionally focused on reliable ingestion and synchronization before social features, because the core user problem is getting camera photos off SD cards and into an accessible, organized workflow.

## Why It Is Interesting

The project is built around a production-style media pipeline rather than a simple file-upload demo. Upload requests create database records immediately, then image processing is delegated to background workers. This keeps API responses fast while allowing expensive work like thumbnail generation, preview creation, metadata extraction, and future deduplication to scale independently.

The architecture also avoids coupling the application directly to a single storage provider. Media access flows through a service abstraction, and the database stores storage identifiers instead of permanent public URLs. That design makes it possible to move from Supabase Storage to S3-compatible storage, Cloudflare Images, or another provider without rewriting the application’s core business logic.

## Core Architecture

- React frontend deployed on Vercel
- Django REST API deployed on Render
- Supabase Postgres for persistent relational data
- Supabase Storage for private original images and generated media assets
- Redis-backed Celery workers for asynchronous image processing
- Token-based API authentication
- Signed media URLs generated on demand instead of permanent public links

## Implemented Features

- User registration and login
- Authenticated dashboard
- Album creation and organization
- Image upload with SHA-256 checksum generation
- Duplicate-upload protection per user
- Private object storage using storage keys
- Signed download URLs for original files
- Asynchronous thumbnail and preview generation
- EXIF metadata extraction pipeline
- Admin-friendly Django data model for users, albums, photos, and metadata

## Scalability Decisions

Photo-Dump separates user-facing API work from media processing. The API stores upload metadata and queues a Celery job, while workers handle image inspection and derivative generation. This separation prevents long-running image operations from blocking user requests and allows the worker tier to scale independently as upload volume grows.

The media service abstraction is another deliberate scalability choice. The application stores `storage_key`, `thumbnail_key`, and `preview_key` values instead of public URLs, keeping storage implementation details isolated from the rest of the system. If media volume or delivery requirements outgrow Supabase Storage, the storage backend can be replaced behind the service interface.

The data model is also structured for future product growth. Albums, photos, and photo metadata are distinct resources, which leaves room for desktop SD-card import, mobile upload/download, public profiles, and social features without forcing a rewrite of the upload pipeline.

## Technical Highlights

- Thin React client consuming an API-first backend
- Django REST Framework serializers and views kept close to resource boundaries
- Service-layer media abstraction for provider independence
- Background worker pipeline for CPU and I/O-heavy media tasks
- Private storage with short-lived signed URLs
- Checksum-based deduplication foundation
- Deployment split across frontend, API, database, storage, Redis, and worker services

## Upcoming Features

- Photo deletion
- Album deletion
- Bulk import
- Export directly to photos library on ios

## Future Direction

The next major milestone is a desktop importer for SD cards using Tauri, React, and TypeScript. The desktop app will consume the same Django API rather than duplicating backend logic, preserving the API-first architecture while improving the ingestion experience for camera-first workflows.
