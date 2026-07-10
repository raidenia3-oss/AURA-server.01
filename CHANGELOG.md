# Changelog

All notable changes to AURA/AME will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/),
and this project adheres to [Semantic Versioning](https://semver.org/).

## [1.0.0] - 2026-07-06

### Added

- **Firebase Auto Setup with Fallback**: Browser automation with automatic fallback to manual config
- **Google AI Studio Integration**: Article analysis with mock mode for development
- **Health Check API**: Endpoint at `/api/health` monitoring all services
- **Dashboard de Monitoreo**: Real-time UI at `/dashboard` with auto-refresh
- **Chrome Extension**: Complete browser extension with popup, background, and content scripts
- **Service Worker**: Offline support with caching strategy
- **SEO Optimizations**: robots.txt, sitemap.xml, meta tags
- **Security Headers**: CSP, HSTS, X-Frame-Options, and more
- **No-JS Fallback**: Functional page without JavaScript
- **GitHub Actions**: Automated deploy to Vercel
- **Godot Game Integration**: WebSocket-based reward system documentation

### Changed

- Improved setup script with multi-level error handling
- Enhanced next.config.js with security and performance optimizations
- Updated documentation structure

### Fixed

- Firebase browser automation crash ("Navigating frame was detached") with automatic fallback
- API error handling with graceful degradation
- Build cache now properly excluded from git

## [0.9.0] - 2026-07-05

### Added

- Initial project structure
- Basic API endpoints
- Firebase configuration templates
- News worker system
- Core agent orchestrator
