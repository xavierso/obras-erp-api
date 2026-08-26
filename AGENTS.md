# Custom Agent Rules for OBRAS_ERP API (Backend)

When working on this FastAPI project, strictly adhere to the following rules:

## 1. Testing & Verification (CRITICAL)
- **Always verify your code**: Before declaring a task finished or pushing code to the repository, you **must** run the test suite using `pytest` to verify that there are no broken tests.
- **Always test new features**: Whenever you create a new endpoint, router, or modify existing business logic, you **must** create or update the corresponding tests in the `tests/` directory.
- **Test execution**: Run `pytest tests/` locally to ensure everything works as expected.

## 2. API Design & Conventions
- **Routing**: Ensure all new endpoints are properly placed in their corresponding routers inside `app/routers/` and included in `app/main.py`.
- **Database**: Use SQLAlchemy with the async engine. Make sure you don't use synchronous DB calls inside async endpoints. Use dependency injection `Depends(get_db)`.
- **Typing**: Use Pydantic models (schemas) for all request and response bodies. Ensure strict typing is maintained.
