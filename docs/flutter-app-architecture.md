# Share Cart Flutter Application Architecture

## Overview

Share Cart is a Flutter mobile application for managing shared grocery/shopping lists.
It integrates with a Spring Boot backend over REST and WebSocket, supports JWT auth,
and includes invite-by-link, QR invite sharing, and deep-link based list joining.

---

## Tech Stack

- **Flutter** with Dart
- **Provider** for state management
- **http** package for REST API calls
- **shared_preferences** for local persistence support
- **flutter_secure_storage** for secure JWT token storage
- **stomp_dart_client** for STOMP-based real-time WebSocket sync
- **app_links** for deep-link handling
- **share_plus** for native share sheet integration
- **qr_flutter** for QR rendering
- **mobile_scanner** for QR scanning
- **image_picker** for receipt/price-tag image capture
- **ShareCart AI extraction API** for server-side image understanding (replaces on-device OCR path)
- **geolocator** for nearby-store lookup and location-aware price submissions
- **Material 3** design system

---

## Project Structure

```text
lib/
├── main.dart                          # Entry point and dependency graph wiring
├── app.dart                           # MaterialApp with Material 3 theming
├── config/
│   └── api_config.dart                # Platform-aware local/prod URL selection + timeouts
├── models/
│   ├── models.dart                    # Barrel export
│   ├── shopping_list_model.dart
│   ├── shopping_list_summary_model.dart
│   ├── item_model.dart
│   ├── member_model.dart
│   ├── auth_response_model.dart
│   ├── list_realtime_event_model.dart
│   ├── api_error_model.dart
│   ├── invite_link_response_model.dart
│   ├── accept_invite_response_model.dart
│   └── invite_preview_model.dart
├── services/
│   ├── services.dart
│   ├── api_client.dart
│   ├── auth_api_service.dart
│   ├── shopping_list_api_service.dart
│   ├── item_api_service.dart
│   ├── invite_api_service.dart
│   ├── price_api_service.dart
│   ├── pending_invite_service.dart
│   └── realtime_sync_service.dart
├── repositories/
│   ├── shopping_list_repository.dart
│   ├── auth_repository.dart
│   └── auth_session_repository.dart
├── providers/
│   ├── auth_provider.dart
│   ├── home_provider.dart
│   ├── list_detail_provider.dart
│   └── price_provider.dart
└── screens/
    ├── auth/
    │   ├── auth_gate.dart
    │   ├── login_screen.dart
    │   └── register_screen.dart
    ├── home/
    │   ├── home_screen.dart
    │   └── widgets/
    │       ├── create_list_dialog.dart
    │       └── open_list_dialog.dart
    ├── invite/
    │   ├── invite_preview_screen.dart
    │   ├── invite_qr_widget.dart
    │   └── scan_qr_screen.dart
    ├── list_detail/
    │   ├── list_detail_screen.dart
    │   └── widgets/
    │       ├── item_tile.dart
    │       ├── add_item_sheet.dart
    │       ├── invite_member_sheet.dart
    │       └── members_sheet.dart
    └── price_scan/
      └── price_scan_screen.dart
```

---

## Layered Architecture

```text
Screens (UI) -> Providers (State) -> Repository -> API Services -> ApiClient
```

- **Screens**: Widgets and user interaction flows.
- **Providers**: `ChangeNotifier` state and async actions.
- **Repository**: Coordinates list/item APIs and app-side persistence where needed.
- **Services**: Per-domain API methods.
- **ApiClient**: Centralized headers, auth token injection, timeout, and error mapping.

Note: Most flows follow this structure end-to-end. The current price-capture feature uses
`PriceProvider -> PriceApiService -> ApiClient` directly and does not yet have a repository layer.

### OCR Migration Status

- Previous approach: on-device OCR in Flutter (`google_mlkit_text_recognition`).
- Current approach: Flutter uploads receipt/price-tag images to ShareCart AI service (`POST /api/v1/receipt/extract`).
- Flutter still performs user confirmation and then sends final confirmed data to Spring Boot for persistence/workflows.

---

## Dependency Injection

Dependencies are wired in `main.dart` with `MultiProvider`:

1. Initialize `SharedPreferences`, `FlutterSecureStorage`, and `ApiClient`.
2. Create API services (`AuthApiService`, `ShoppingListApiService`, `ItemApiService`, `InviteApiService`, `PriceApiService`).
3. Create repositories (`AuthSessionRepository`, `AuthRepository`, `ShoppingListRepository`).
4. Create cross-cutting services (`RealtimeSyncService`, `PendingInviteService`).
5. Provide them at root and create `AuthProvider` from repository dependencies.
6. `AuthGate` builds authenticated flow and can resume pending invite-token navigation.

---

## Data Models

| Model | Purpose |
|---|---|
| `ShoppingListModel` | Full shopping list with items and members |
| `ShoppingListSummaryModel` | Summary list row data for home screen |
| `ItemModel` | Individual list item |
| `MemberModel` | Membership entry with role metadata |
| `AuthResponseModel` | JWT auth response payload |
| `ListRealtimeEventModel` | WebSocket event payload for list refresh |
| `ApiErrorModel` | Backend error payload mapping |
| `InviteLinkResponseModel` | Invite-link generation response |
| `AcceptInviteResponseModel` | Accept-invite response (listId/message) |
| `InvitePreviewModel` | Public invite preview payload |

---

## API Client

`ApiClient` centralizes HTTP behavior:

- JSON request/response handling for `get`, `post`, `put`, `delete`
- `getPublic` for unauthenticated endpoints (invite preview)
- Automatic `Authorization: Bearer <token>` header for protected calls
- Unauthorized callback trigger on `403`
- Connection timeout via `ApiConfig.connectionTimeout`
- Error conversion into `ApiException(ApiErrorModel)`

---

## Environment and URLs

`ApiConfig` supports local and production targets:

- `useProductionServer = true` uses Render backend and WSS endpoint.
- `useProductionServer = false` uses platform-aware localhost variants.
- Primary ShareCart AI service base URL (production): `https://sharecart-ai-services.onrender.com`
- Local host mapping:
  - Android emulator: `10.0.2.2`
  - iOS/macOS: `127.0.0.1`
  - Web: `localhost`
- Current connection/receive timeout constants are `60s`.

---

## API Coverage

Implemented backend endpoint coverage:

| Action | Method | Endpoint | Service |
|---|---|---|---|
| Register | `POST` | `/auth/register` | `AuthApiService` |
| Login | `POST` | `/auth/login` | `AuthApiService` |
| Get my lists | `GET` | `/lists/me` | `ShoppingListApiService` |
| Create list | `POST` | `/lists` | `ShoppingListApiService` |
| Get list by ID | `GET` | `/lists/{id}` | `ShoppingListApiService` |
| Invite by user ID | `POST` | `/lists/{id}/invite` | `ShoppingListApiService` |
| Generate invite link | `POST` | `/lists/{id}/invite-link` | `InviteApiService` |
| Invite preview (public) | `GET` | `/invites/{token}` | `InviteApiService` |
| Accept invite | `POST` | `/invites/{token}/accept` | `InviteApiService` |
| Add item | `POST` | `/lists/{listId}/items` | `ItemApiService` |
| Update item | `PUT` | `/items/{id}` | `ItemApiService` |
| Delete item | `DELETE` | `/items/{id}` | `ItemApiService` |
| Extract items from image (AI) | `POST` | `/api/v1/receipt/extract` | `PriceApiService` |
| Capture raw OCR text | `POST` | `/prices/capture` | `PriceApiService` |
| Confirm extracted price | `POST` | `/prices/confirm` | `PriceApiService` |
| Compare submitted price | `POST` | `/prices/compare` | `PriceApiService` |
| Nearby stores by location | `GET` | `/stores/nearby?lat={lat}&lon={lon}` | `PriceApiService` |

Note: `/api/v1/receipt/extract` is now the primary extraction path. Legacy OCR-specific endpoints can be retained only if your Spring Boot flow still requires them.

---

## Invite, Deep Link, and QR Flow

### Invite Link Generation

- Owners can generate invite links from list-detail UI actions.
- Sharing uses `share_plus` native share sheet.

### Deep Link Handling

- `main.dart` listens for cold-start and in-app links via `app_links`.
- Supported pattern: `https://sharecart.app/invite/{token}`.
- If authenticated: navigate directly to `InvitePreviewScreen(token)`.
- If unauthenticated: store token in `PendingInviteService`.
- `AuthGate` consumes pending token after login and routes to preview.

### QR Flow

- `InviteQrWidget` renders QR from full invite URL.
- `ScanQrScreen` scans QR and validates ShareCart invite URL structure.
- On valid scan: extract token and navigate to `InvitePreviewScreen`.

### Invite Preview + Join

`InvitePreviewScreen`:

- Fetches preview with public endpoint (`getInvitePreview`).
- Handles join via `acceptInvite`.
- Handles status outcomes:
  - `200`: navigate to joined list
  - `400`: expired invite
  - `404`: invalid invite
  - `409`: already member
  - `403`: redirect to login

---

## State Management

### AuthProvider

- Restores and maintains authenticated session state.
- Exposes `login`, `register`, and `logout` actions.

### HomeProvider

- Loads lists from backend (`GET /lists/me`).
- Supports list creation and explicit refresh.

### ListDetailProvider

- Manages a single list detail context.
- Handles add/update/toggle/delete item operations.
- Handles invite-by-userId action.
- Refreshes list state after write operations.
- Subscribes to real-time events via `RealtimeSyncService`.

### PriceProvider

- Captures image input using camera (`ImagePicker`).
- Sends image to ShareCart AI extraction service (`POST /api/v1/receipt/extract`).
- Receives structured item/price extraction response for user review and correction.
- Fetches nearby stores using current GPS coordinates.
- Submits user-confirmed final data via `PriceApiService`.

---

## UI Screens (High-Level)

- **Auth**: `AuthGate`, `LoginScreen`, `RegisterScreen`
- **Home**: list overview, refresh, create/open list, QR scan entry action
- **List Detail**: list items, member management, invite/share actions
- **Invite**: preview, QR generation widget, QR scan screen
- **Price Scan**: receipt/price-tag capture, AI extraction preview, price confirmation, nearby stores

---

## Local Persistence Notes

- Auth tokens are persisted in secure storage (`flutter_secure_storage`).
- `SharedPreferences` is initialized and injected into `ShoppingListRepository`; list persistence logic is not yet actively used.
- Home list rendering currently relies on backend `GET /lists/me` as source of truth.

---

## Error Handling

Backend errors are normalized in `ApiClient` as `ApiException` and surfaced at provider/UI layers.
Typical status handling used across screens:

| Status | Meaning | UI Behavior |
|---|---|---|
| `400` | Validation/expired token | Show contextual message |
| `403` | Unauthorized/forbidden | Redirect to login or show permission message |
| `404` | Not found/invalid token | Show not-found or invalid-link message |
| `409` | Business conflict | Show conflict message and preserve UX flow |
| `500` | Server error | Show generic retry guidance |

---

## Run and Verify

```bash
flutter run
```

For backend targeting:

- Use `ApiConfig.useProductionServer = true` for deployed Render backend.
- Use `ApiConfig.useProductionServer = false` for local Spring Boot backend.

---

## Extensibility

The current architecture supports straightforward growth:

- Add endpoints by extending service classes
- Add feature screens with scoped providers
- Add repository caching/offline policies
- Move to named routes/router package when navigation complexity grows
- Extend real-time and invite flows without cross-layer coupling
