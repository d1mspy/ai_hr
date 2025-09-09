CREATE TABLE "user"(
    id SMALLSERIAL PRIMARY KEY,
    summary TEXT,
    meta TEXT,
    hard_topics JSONB NOT NULL DEFAULT '[]'::jsonb,
    soft_topics JSONB NOT NULL DEFAULT '[]'::jsonb
);

ALTER TABLE "user"
ADD CONSTRAINT hard_topics_is_array CHECK (jsonb_typeof(hard_topics) = 'array');
ADD CONSTRAINT soft_topics_is_array CHECK (jsonb_typeof(soft_topics) = 'array');