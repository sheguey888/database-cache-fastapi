# Security and persistence report

## Database schema

The SQLite database is managed with SQLAlchemy. `users` stores a unique email and
only a password hash. `conversations` belongs to one user through `user_id`, and
`messages` belongs to one conversation through `conversation_id`. Each submitted
prompt is stored as a `user` message and its generated reply as an `assistant`
message.

## Authentication flow

`POST /auth/register` validates the email and password length, hashes the password
with Argon2 through `pwdlib`, and never persists the raw password. `POST
/auth/login` verifies the hash and returns a short-lived (30 minute) JWT. Protected
routes read the bearer token with `OAuth2PasswordBearer`, validate its signature
and expiry, then load the user identified by the `sub` claim. Set `SECRET_KEY` in
the environment for deployments; the built-in value is only for local development.

## Ownership rule

Every conversation query includes both the requested conversation ID and the
authenticated user's ID. The same check runs before adding messages. An
unowned or missing conversation returns `404 Conversation not found`, avoiding a
data leak about whether another user's ID exists. Listing conversations filters
by the authenticated user as well.

## Private-data test

`tests/test_security_persistence.py::test_user_cannot_read_or_modify_another_users_conversation`
registers two users, creates a conversation for user A, and verifies that user B
cannot read it, cannot add messages to it, and sees an empty conversation list.

## Cache note

This checkpoint does not cache AI results. A future in-memory or Redis cache can
avoid repeating non-sensitive, deterministic AI work, but it is temporary:
entries can expire or disappear during a restart. SQLite remains the permanent
source of truth for users, conversations, and messages.
