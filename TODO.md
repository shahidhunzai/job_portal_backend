# TODO

- [ ] Fix project startup/runtime errors (currently reported stack points to `asyncio.py` during `self.connect()`)
- [ ] Inspect `job_portal/settings.py` for duplicated/invalid settings that could cause startup issues (observed duplicated `import os` and BASE_DIR + large corruption/encoding artifacts)
- [ ] Normalize/repair `job_portal/settings.py` to valid Python settings file
- [ ] Verify Django can start (`python manage.py check` / runserver)
- [ ] Re-run failing endpoint(s) to confirm `self.connect()` error is resolved

