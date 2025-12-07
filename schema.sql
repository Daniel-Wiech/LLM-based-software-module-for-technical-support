CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    surname TEXT NOT NULL,
    login TEXT UNIQUE NOT NULL,
    mail TEXT UNIQUE NULL,
    password TEXT NOT NULL,
    role TEXT NOT NULL,
    created TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE conversations (
    id SERIAL PRIMARY KEY,
    user_id INT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    created TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE history (
    id SERIAL PRIMARY KEY,
    conversation_id INT NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    created TIMESTAMPTZ DEFAULT NOW(),
    usermessage TEXT NOT NULL,
    llmmessage TEXT NOT NULL,
    rating BOOLEAN
);

CREATE TABLE refresh_tokens (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id),
    token TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at TIMESTAMPTZ NOT NULL,
    revoked BOOLEAN NOT NULL DEFAULT FALSE
);
