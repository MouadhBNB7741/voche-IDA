# Backend Progress Tracking

## Completed Tasks

* ✅ Auth endpoints implemented (`app/api/v1/auth.py`)
* ✅ Profile endpoints implemented (`app/api/v1/users.py`)
* ✅ JWT integration
* ✅ Raw SQL integration via Model Layer
* ✅ Existing DB schema respected

---

## 🆕 Architecture Enhancements

* ✅ Introduced model layer abstraction (Raw SQL encapsulated) in `app/models/`

  * `base_model.py`: Base DB logic
  * `user_model.py`: User CRUD
  * `profile_model.py`: Profile logic
  * `password_reset_model.py`: Token logic
* ✅ Refactored Pydantic Schemas to `app/schemas/`

  * `auth.py`: Authentication schemas
  * `user.py`: User/Profile schemas
  * Removed duplicate logic from `models/schemas.py`
  * Fixed type hinting (`Optional`, `Union`, `List`)
* ✅ Removed SQL from route layer (`auth.py`, `users.py`)
* ✅ Centralized query logic in models
* ✅ Added full pytest test suite in `app/tests/`
* ✅ Added QA validation pass
* ✅ Improved error handling consistency
* ✅ Verified DB schema compliance

---

## Testing Coverage

* ✅ Auth endpoints fully tested (`test_auth.py`)

  * Register, Login, Me, Update Password
* ✅ Profile endpoints fully tested (`test_users.py`)

  * Update, Completion Logic
* ✅ Schema validation tested (`test_schemas.py`)
* ✅ Edge cases covered (invalid emails, bad passwords)
* ✅ Token lifecycle covered (reset flow basics)
* ✅ Security flows validated

---

## Pending Tasks

* ⬜ Implementation of other domains (Clinical Trials, Community, etc.)
* ⬜ Integration with centralized Email Service
* ⬜ Rate limiting implementation
* ⬜ Run tests in CI/CD pipeline

---

## Notes

* **Architecture**: Clean "Model-Service-Controller" style.
* **Schemas**: Separated into domain-specific files for better maintainability.
* **Security**: Security is hardened. No PII leaks in responses.
* **Testing**: Tests use the dev database currently; ensure a separate test DB is configured for CI.

---

## Guidance for Azzedine

Hi! Here’s a **simple, detailed explanation** of how the backend is structured :

1. **Model Layer**

   * All database logic is in `app/models/`
   * Routes (`auth.py`, `users.py`) **don’t talk to the DB directly**.
     * Instead, they call functions in models like `UserModel.create_user()` or `ProfileModel.get_profile()`

2. **Schemas**

   * Schemas define the **shape of data** that goes in and out of the API.
     * `app/schemas/auth.py` → login/register/reset requests & responses
     * `app/schemas/user.py` → user profile responses and updates
   * Pydantic automatically **validates the data** for you. For example, email must be valid, password must be 8+ chars.

3. **Raw SQL + asyncpg**

   * Instead of using an ORM like SQLAlchemy, we write **safe parameterized queries** in the models.
   * `asyncpg` allows **asynchronous database calls**, which is faster when many users hit the API.

4. **How to continue safely**

   * **Always import schemas from `app.schemas`**, When creating new endpoints:

     1. Add SQL logic in the **model layer**.
     2. Create Pydantic schema in `auth.py` or `user.py`.
     3. Use schema in the route (`api/v1/...`) for validation and response.
     4. Write **pytest tests** to validate your endpoint.
   * **Check `tests/`** to see examples of how requests/responses are validated.

1. **Tips**

   * Use `pytest -v` to run tests and see detailed results.
   * Use `mypy` for type checking if unsure about types.
   * For any data returned from the DB that is JSONB, always **deserialize it** before using in Pydantic models.

