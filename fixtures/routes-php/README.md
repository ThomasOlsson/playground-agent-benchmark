# routes-php fixture

A Laravel-style routes-only fixture. Never executed; read/edited as text.

## Intended shape

- `routes/web.php` — six routes using `Route::get/post/put/delete`, each pointing at a controller method.
- `app/Http/Controllers/UserController.php` — stub with method signatures only.
- `app/Http/Controllers/ProductController.php` — stub with method signatures only.

## Cases that depend on this fixture

- `RO-001` — read-only: list every route as JSON.

Any change to the number, method, path, or handler of any route is benchmark drift and requires bumping `schema_version` on dependent cases.
