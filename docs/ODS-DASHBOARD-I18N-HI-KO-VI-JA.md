# ODS Dashboard i18n — Hindi, Korean, Vietnamese and Japanese

This LEONES contribution prepares the next ODS Dashboard i18n expansion after the initial English/Spanish/Simplified Chinese work.

## Scope

Add four locales:

| Code | Language | Native label |
| --- | --- | --- |
| hi | Hindi | हिन्दी |
| ja | Japanese | 日本語 |
| ko | Korean | 한국어 |
| vi | Vietnamese | Tiếng Việt |

English remains the fallback. Existing Spanish and Simplified Chinese translations are preserved.

## ODS files affected by the installer

- `ods/extensions/services/dashboard/src/i18n/index.js`
- `ods/extensions/services/dashboard/src/i18n/hi.js`
- `ods/extensions/services/dashboard/src/i18n/ja.js`
- `ods/extensions/services/dashboard/src/i18n/ko.js`
- `ods/extensions/services/dashboard/src/i18n/vi.js`
- `ods/extensions/services/dashboard/src/i18n/index.test.js`

No backend or service behavior changes are intended.

## Design

The implementation reuses the existing dependency-free i18n layer:

- central supported-language list;
- native language selector;
- local persistence;
- English fallback;
- translation dictionaries using the existing keys;
- no new i18n dependency.

The dictionaries intentionally inherit the English dictionary and override the translated strings. This keeps newly added keys safe through the existing English fallback.

## Installer

Use:

`tools/apply-ods-dashboard-i18n-hi-ko-vi-ja.py`

The installer does not create commits. It requires an ODS checkout that already contains the initial Dashboard i18n layer.

## Validation

After applying it in an ODS checkout:

```bash
cd ods/extensions/services/dashboard
pnpm test -- --run src/i18n
pnpm build
pnpm lint
git diff --check
```

The full Dashboard test suite should be run before opening an upstream ODS PR.

## Relationship to the first ODS PR

This is deliberately a separate contribution. It does not modify or replace the original Spanish/Simplified Chinese PR.
