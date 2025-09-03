/* тут будет инициализация бд когда бд будет спроектирована */

/* тестовая инициализация */
CREATE TABLE test(
    id uuid primary key,
    created_at timestamp not null,
    updated_at timestamp not null,
    string text
)
