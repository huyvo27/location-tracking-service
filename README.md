# Location Tracking Service

## Overview
The Location Tracking Service is a real-time, group-based location-sharing application designed to enable users to track and share their locations within defined groups. Built with FastAPI, PostgreSQL, and Redis, it supports frequent location updates (e.g., every 2-3 seconds) and is optimized for scalability with async I/O. The service leverages asynchronous programming and SQLAlchemy for efficient database operations and provides a RESTful API for seamless integration.

## Features

- **Real-Time Location Updates:** Share and track group members' locations in real-time using WebSocket technology.

- **Group Management:** Create and manage groups, ensuring only authorized users can access location data.

- **Scalable Architecture:** Handles high query rates with async PostgreSQL (asyncpg) and FastAPI for low-latency performance.

- **User Authentication:** Secure user management with FastAPI's dependency injection and SQLAlchemy ORM.

- **Customizable Configuration:** Easily configure environment variables and database settings for deployment.

## Prerequisites

- Python 3.9+

- PostgreSQL 13+

- Docker (optional, for containerized deployment)

- Redis 6+ (for store locations data and caching)

- Poetry (for dependency management)

## Installation

### Clone the Repository
```bash
git clone https://github.com/huyvo27/location-tracking-service.git
cd location-tracking-service
```
### Set Up a Virtual Environment

```bash
python -m venv .venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### Install Dependencies
```bash
poetry install --with dev (for dev environment)
```

### Configure Environment Variables
Create a `.env` file based on the provided `.env.example`:

```bash
cp .env.example .env
# or
mv .env.example .env
```

Edit `.env` to include your PostgreSQL database URL, and other settings:
```bash
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/app_db
SECRET_KEY=your-secret-key
REDIS_URLs=your-redis-urls
```

### Run the Application
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
# or
make run
```
## Usage

1. **Start the Server:** Run the application using the command above.

2. **Access the API:** Open `http://localhost:8000/v1/docs` in your browser to interact with the Swagger UI for API endpoints.

3. **Create a User:** Use the `/auth/register` endpoint to create a user account.

4. **Manage Groups:** Use endpoints like `/groups/create` and `/groups/join` to manage group membership.

5. **Share Location:** Use WebSocket endpoint `/ws/location` to send and receive real-time location updates.

## System Architecture
![DB Schema](./docs/architecture.png)

The service follows a layered architecture for scalability and real-time performance:

- **Client Layer:** Mobile app use HTTP/REST and WebSocket to interact with the server.

- **API Gateway:** Acts as a single entry point for all HTTP and WebSocket traffic. Handles routing, authentication forwarding, rate limiting, and can be backed by NGINX or an API management layer (e.g., Kong or Envoy).

- **Application Layer (LTS Pods):**
    - LTS (Location Tracking Service) instances are deployed as multiple pods behind a load balancer.
    - Each pod is stateless and handles both REST and WebSocket requests.
    - Built with FastAPI and powered by asynchronous I/O (`psycopg` + `SQLAlchemy` + `redis.asyncio`).

- **Data Layer:**
    - PostgreSQL: stores persistent data (`users`, `groups`, `membership`)
    - Redis Cluster: Used for caching, group state management, and real-time Pub/Sub broadcasting.

- **Infrastructure:**
    - LTS pods are horizontally scalable and stateless.
    - Redis nodes can be clustered or sharded depending on load and reliability needs.

## API Endpoints
### Authentication
- **POST /api/v1/auth/login:** Authenticate user with username and password, returning an access token.
- **POST /api/v1/auth/logout:** Placeholder for logout functionality (token invalidation or session management).
- **POST /api/v1/auth/register:** Create a new user and return an access token.
### Groups
- **GET /api/v1/groups:** Retrieve a paginated list of groups (filter by joined or owned groups).
- **POST /api/v1/groups:** Create a new group.
- **GET /api/v1/groups/{group_uuid}:** Get detailed information about a specific group.
- **DELETE /api/v1/groups/{group_uuid}:** Delete a group (owner only).
- **PUT /api/v1/groups/{group_uuid}:** Update group information (owner only).
- **POST /api/v1/groups/{group_uuid}/members:** Join a group by creating a membership.
- **DELETE /api/v1/groups/{group_uuid}/members/me:** Allow the current user to leave a group.
- **DELETE /api/v1/groups/{group_uuid}/members/{member_uuid}:** Remove a user from a group (owner only).
- **PUT /api/v1/groups/{group_uuid}/members/me/location:** Update the current user's location in a group.
- **GET /api/v1/groups/{group_uuid}/members/locations:** Retrieve locations of members in a group.
### Users
- **GET /api/v1/users:** Get a paginated list of users.
- **POST /api/v1/users:** Create a new user.
- **GET /api/v1/users/me:** Get details of the current user.
- **PUT /api/v1/users/me:** Update the current user's information.
- **GET /api/v1/users/{user_uuid}:** Get details of a specific user.
- **PUT /api/v1/users/{user_uuid}:** Update a specific user's information.
- **DELETE /api/v1/users/{user_uuid}:** Delete a specific user.

## Database Structure
### Relational DB Schema
![DB Schema](./docs/db/erd.png)
### Redis Schema

##### `member:{group_uuid}`

* Type: `Set`
* Value: each item is a `user_uuid` (string)
* TTL: refreshed on update and creation

##### `location:{group_uuid}`

* Type: `Hash`
* Field: `user_uuid`
* Value: JSON-encoded location object (as string), example:

  ```json
  {
    "user_uuid": "user-1",
    "latitude": 10.123,
    "longitude": 106.456,
    "timestamp": 1720992121,
    "nickname": "..." //(optional)
  }
  ```
* TTL: refreshed on update

#### `group:{group_uuid}:location`

* Type: `Pub/Sub Channel`
* Message: JSON payload of the updated location
* Example:

  ```json
  {
    "user_uuid": "user-1",
    "latitude": 10.123,
    "longitude": 106.456,
    "timestamp": 1720992121,
    "nickname": "..." //(optional)
  }
  ```

## Websocket Endpoint
- **/groups/{group_uuid}/ws**: Establishes a WebSocket connection for real-time group location tracking. Requires user authentication and group membership. Supports the following actions:

    - `get_locations`: Retrieves current locations of all group members.
    - `ping`: Checks connection status, responding with a pong message.
    - `update_location`: Updates the user's location (latitude, longitude, timestamp, optional nickname) and broadcasts it to other group members via Redis pub/sub.
    - On connection, sends initial group member locations. Listens for location updates and broadcasts them to connected clients, excluding the sender's own updates.

## Testing
```bash
make test # for both unit and integration tests
make unit-test # only unit tests
make integration-test # only integration tests
```

## License
This project is licensed under the MIT License.