# Mergington High School Activities API

A super simple FastAPI application that allows students to view and sign up for extracurricular activities.

## Features

- View all available extracurricular activities
- Sign up for activities
- View active announcements; signed-in teachers can create, edit, schedule, and delete them

## Getting Started

1. Install the dependencies:

   ```
   pip install -r requirements.txt
   ```

2. Start MongoDB on `localhost:27017`, then run the application from the repository root:

   ```
   uvicorn src.app:app --reload
   ```

3. Open your browser and go to:
   - API documentation: http://localhost:8000/docs
   - Alternative documentation: http://localhost:8000/redoc

## API Endpoints

| Method | Endpoint                                                          | Description                                                         |
| ------ | ----------------------------------------------------------------- | ------------------------------------------------------------------- |
| GET    | `/activities`                                                     | Get all activities with their details and current participant count |
| POST   | `/activities/{activity_name}/signup?email=student@mergington.edu` | Sign up for an activity                                             |
| POST   | `/auth/login` | Sign in with a JSON body containing `username` and `password`; sets an eight-hour HttpOnly session cookie |
| GET    | `/auth/check-session` | Return the signed-in teacher (session cookie required) |
| POST   | `/auth/logout` | Revoke the session and clear its cookie |
| GET    | `/announcements` | Public list: start date is unset or <= now, expiration date > now |
| GET    | `/announcements/all` | List all announcements (session cookie required) |
| POST   | `/announcements` | Create an announcement (session cookie required); returns 201 |
| PUT    | `/announcements/{id}` | Replace an announcement's message and dates (session cookie required) |
| DELETE | `/announcements/{id}` | Delete an announcement (session cookie required); returns 204 |

Announcement create/update bodies contain `message` (nonblank, up to 2,000 characters),
`expiration_date` (required, `YYYY-MM-DD`), and `start_date` (optional, `YYYY-MM-DD` or
`null`). A supplied start date must be strictly before expiration. Dates represent
midnight UTC: a message expires at the **beginning** of its expiration date. Past
dates are allowed, so expired announcements can still be edited. Responses include
these fields and an `id`. Invalid input returns 422; missing announcements return
404; unauthenticated management requests return 401.

The header's Announcements button is available after teacher login. Its dialog
shows active, scheduled, and expired messages with add/edit/delete controls,
inline validation, and deletion confirmation. Escape closes the dialog and restores
focus. Public banners refresh every minute and after management changes.

**Authentication API change:** login credentials now go in the JSON body, not
query parameters. Session checks now require the server-issued cookie instead of
a username. Existing saved browser user data alone does not authenticate a user;
users must sign in again. Cookies use SameSite Strict and are marked Secure on
HTTPS requests. Serve the application over HTTPS in production.

## Data Model

The application uses a simple data model with meaningful identifiers:

1. **Activities** - Uses activity name as identifier:

   - Description
   - Schedule
   - Maximum number of participants allowed
   - List of student emails who are signed up

2. **Students** - Uses email as identifier:
   - Name
   - Grade level

3. **Announcements** - Uses a MongoDB-generated identifier:
   - Message
   - Required expiration date
   - Optional start date

Data is persisted in MongoDB's `mergington_high` database. Initialization creates
sample activities, teachers, and an example announcement. The example announcement
expires 30 days after initialization and is seeded only when its collection is
first created, so deleting all announcements does not restore it on restart.
Teacher sessions store hashed random tokens and expire automatically.
