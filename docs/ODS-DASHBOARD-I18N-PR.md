# ODS Dashboard Internationalization — PR Documentation

This document describes the proposed ODS Dashboard internationalization contribution.

The implementation is intentionally small and dependency-free. English remains the default and fallback language. Spanish and Simplified Chinese are added as the first translated locales.

---

# English

## Title

feat(dashboard): add Spanish and Simplified Chinese dashboard i18n

## Summary

This contribution adds a small native internationalization layer to the ODS Dashboard.

Initial scope:
- First-boot setup wizard.
- Language selection during first boot.
- Dashboard → Settings → Profile language selection.
- Persistent language preference.
- English as default and fallback.
- Spanish (es).
- Simplified Chinese (zh-CN).
- Focused unit and component tests.

No backend behavior, service lifecycle, authentication flow, model selection, or API contract is changed.

## User experience

A language selector is available during first boot before configuration is completed.

The same preference can later be changed from Dashboard → Settings → Profile.

The preference is stored locally under ods.language.v1 and remains separate from the existing local profile data.

## Supported languages

| Code | Language | Native label |
| --- | --- | --- |
| en | English | English |
| es | Spanish | Español |
| zh-CN | Simplified Chinese | 简体中文 |

English is used when no language has been selected, when the stored language is invalid, or when a selected dictionary does not contain a requested key.

## Implementation

New files:
- ods/extensions/services/dashboard/src/i18n/index.js
- ods/extensions/services/dashboard/src/i18n/en.js
- ods/extensions/services/dashboard/src/i18n/es.js
- ods/extensions/services/dashboard/src/i18n/zh-CN.js
- ods/extensions/services/dashboard/src/i18n/LanguageSelector.jsx
- ods/extensions/services/dashboard/src/i18n/index.test.js
- ods/extensions/services/dashboard/src/i18n/LanguageSelector.test.jsx

Modified files:
- ods/extensions/services/dashboard/src/pages/FirstBoot.jsx
- ods/extensions/services/dashboard/src/components/settings/ProfileSettings.jsx

SettingsModal.jsx is deliberately not modified.

## Design decisions

### No new i18n dependency

The Dashboard already has React and browser storage. A small native translation layer is sufficient for the initial scope and avoids adding another dependency.

### useSyncExternalStore

The language preference is observable in the current browser context and through storage events without introducing a global provider solely for language state.

### Flat translation keys

Keys such as firstBoot.welcome.title and profile.save are easy to audit and extend.

### English fallback

Translation resolution is:
1. selected locale;
2. English;
3. the translation key itself.

This prevents incomplete translations from producing empty UI.

### Native language selector

The selector uses the browser native select element. This preserves normal keyboard/accessibility behavior and avoids another UI dependency.

## Scope boundaries

This contribution does not attempt to translate:
- backend-generated error messages;
- service names;
- product names;
- API payloads;
- URLs;
- environment variable names;
- model names;
- authentication semantics.

Product and technical identifiers such as ODS, ODS Talk, Hermes, n8n, Settings, Setup, Owner, Extensions, and ODS_DEVICE_NAME remain recognizable.

## Compatibility with current work

The implementation avoids the files and areas with the highest known collision risk.

In particular:
- existing FirstBoot progress helpers remain in place;
- existing Back-button accessibility attributes remain in place;
- SettingsModal is not changed;
- Profile remains the existing Dashboard → Settings → Profile surface.

## Validation

Focused tests cover:
- English default;
- language persistence;
- invalid-language fallback;
- Spanish translation lookup;
- Simplified Chinese translation lookup;
- supported-language enumeration;
- language selector persistence and UI update.

The full Dashboard test suite should also be run before opening the upstream PR.

## Review checklist

- [ ] English remains the default.
- [ ] Spanish works during first boot.
- [ ] Simplified Chinese works during first boot.
- [ ] Language persists after reload.
- [ ] Settings → Profile can change the language.
- [ ] Invalid stored language falls back to English.
- [ ] Missing translation keys fall back to English.
- [ ] Existing FirstBoot progress behavior remains unchanged.
- [ ] Existing owner-card flow remains unchanged.
- [ ] Existing Profile photo/name behavior remains unchanged.
- [ ] No backend/API behavior changes.
- [ ] Dashboard tests pass.
- [ ] git diff --check passes.

---

# Español

## Título

feat(dashboard): añadir i18n del dashboard en español y chino simplificado

## Resumen

Esta aportación añade una pequeña capa nativa de internacionalización al Dashboard de ODS.

Alcance inicial:
- asistente de configuración inicial;
- selector de idioma durante el primer arranque;
- selector de idioma en Dashboard → Settings → Profile;
- persistencia de la preferencia;
- inglés como idioma predeterminado y de reserva;
- español (es);
- chino simplificado (zh-CN);
- pruebas unitarias y de componente específicas.

No se modifica el comportamiento del backend, el ciclo de vida de servicios, la autenticación, la selección de modelos ni los contratos de API.

## Experiencia de usuario

Durante el primer arranque aparece un selector de idioma antes de completar la configuración.

La misma preferencia puede modificarse posteriormente desde Dashboard → Settings → Profile.

La preferencia se almacena localmente mediante ods.language.v1 y permanece separada de los datos del perfil local existente.

## Idiomas

| Código | Idioma | Nombre nativo |
| --- | --- | --- |
| en | Inglés | English |
| es | Español | Español |
| zh-CN | Chino simplificado | 简体中文 |

El inglés se utiliza cuando no existe una selección previa, cuando el valor almacenado no es válido o cuando falta una clave de traducción en el idioma seleccionado.

## Implementación

Archivos nuevos:
- ods/extensions/services/dashboard/src/i18n/index.js
- ods/extensions/services/dashboard/src/i18n/en.js
- ods/extensions/services/dashboard/src/i18n/es.js
- ods/extensions/services/dashboard/src/i18n/zh-CN.js
- ods/extensions/services/dashboard/src/i18n/LanguageSelector.jsx
- ods/extensions/services/dashboard/src/i18n/index.test.js
- ods/extensions/services/dashboard/src/i18n/LanguageSelector.test.jsx

Archivos modificados:
- ods/extensions/services/dashboard/src/pages/FirstBoot.jsx
- ods/extensions/services/dashboard/src/components/settings/ProfileSettings.jsx

No se modifica SettingsModal.jsx.

## Decisiones de diseño

### Sin nueva dependencia de i18n

El Dashboard ya dispone de React y almacenamiento del navegador. Una capa nativa pequeña es suficiente para el alcance inicial y evita añadir una dependencia adicional.

### useSyncExternalStore

La preferencia de idioma puede observarse en el contexto actual del navegador y mediante eventos de almacenamiento sin introducir un provider global únicamente para el idioma.

### Claves planas

Claves como firstBoot.welcome.title y profile.save permiten revisar y ampliar fácilmente los diccionarios.

### Fallback en inglés

El orden de resolución es:
1. idioma seleccionado;
2. inglés;
3. clave de traducción.

Así, una traducción incompleta nunca deja elementos de interfaz vacíos.

### Selector nativo

Se utiliza el elemento HTML select del navegador, manteniendo accesibilidad y evitando otra dependencia de componentes.

## Límites del alcance

No se intenta traducir:
- mensajes generados dinámicamente por el backend;
- nombres de servicios;
- nombres de producto;
- payloads de API;
- URLs;
- variables de entorno;
- nombres de modelos;
- semántica de autenticación.

Se mantienen identificadores técnicos y de producto como ODS, ODS Talk, Hermes, n8n, Settings, Setup, Owner, Extensions y ODS_DEVICE_NAME.

## Compatibilidad con el trabajo actual

La implementación evita modificar las zonas con mayor riesgo de conflicto.

En particular:
- se conservan los helpers de progreso de FirstBoot;
- se conservan los atributos de accesibilidad de los botones Back;
- no se modifica SettingsModal;
- Profile continúa siendo la pestaña existente Dashboard → Settings → Profile.

## Validación

Se añaden pruebas específicas para:
- inglés como idioma predeterminado;
- persistencia;
- fallback ante idioma inválido;
- traducciones en español;
- traducciones en chino simplificado;
- enumeración de idiomas;
- persistencia y actualización visual del selector.

Antes de abrir el PR upstream se debe ejecutar también toda la batería de pruebas del Dashboard.

## Checklist de revisión

- [ ] Inglés sigue siendo el idioma predeterminado.
- [ ] El selector de español funciona durante el primer arranque.
- [ ] El selector de chino simplificado funciona durante el primer arranque.
- [ ] El idioma persiste tras recargar.
- [ ] Settings → Profile permite cambiarlo.
- [ ] Un idioma almacenado inválido vuelve a inglés.
- [ ] Las claves inexistentes hacen fallback a inglés.
- [ ] El progreso de FirstBoot sigue funcionando.
- [ ] El flujo de owner card sigue funcionando.
- [ ] Nombre y foto del Profile siguen funcionando.
- [ ] No hay cambios de backend/API.
- [ ] Las pruebas del Dashboard pasan.
- [ ] git diff --check pasa.

---

# 中文（简体）

## 标题

feat(dashboard): 为 Dashboard 增加西班牙语和简体中文国际化

## 概要

本贡献为 ODS Dashboard 增加一个轻量、原生、无额外依赖的国际化层。

第一阶段范围：
- 首次启动设置向导；
- 首次启动时的语言选择；
- Dashboard → Settings → Profile 中的语言选择；
- 语言偏好的持久化；
- 英语作为默认语言和回退语言；
- 西班牙语（es）；
- 简体中文（zh-CN）；
- 针对性的单元测试和组件测试。

不会修改后端行为、服务生命周期、认证流程、模型选择或 API 契约。

## 用户体验

首次启动时，在完成配置之前即可选择语言。

之后可以在 Dashboard → Settings → Profile 中再次修改语言。

语言偏好保存在 ods.language.v1，并与现有的本地 Profile 数据分开保存。

## 支持的语言

| 代码 | 语言 | 原生名称 |
| --- | --- | --- |
| en | 英语 | English |
| es | 西班牙语 | Español |
| zh-CN | 简体中文 | 简体中文 |

以下情况使用英语：
1. 用户尚未选择语言；
2. 已保存的语言值无效；
3. 当前语言缺少某个翻译 key。

## 实现

新增文件：
- ods/extensions/services/dashboard/src/i18n/index.js
- ods/extensions/services/dashboard/src/i18n/en.js
- ods/extensions/services/dashboard/src/i18n/es.js
- ods/extensions/services/dashboard/src/i18n/zh-CN.js
- ods/extensions/services/dashboard/src/i18n/LanguageSelector.jsx
- ods/extensions/services/dashboard/src/i18n/index.test.js
- ods/extensions/services/dashboard/src/i18n/LanguageSelector.test.jsx

修改文件：
- ods/extensions/services/dashboard/src/pages/FirstBoot.jsx
- ods/extensions/services/dashboard/src/components/settings/ProfileSettings.jsx

明确不修改 SettingsModal.jsx。

## 设计决策

### 不增加新的 i18n 依赖

Dashboard 已经使用 React，并可以使用浏览器本地存储。对于第一阶段，一个小型原生国际化层已经足够，同时避免增加额外依赖。

### useSyncExternalStore

语言偏好通过 React 的 useSyncExternalStore 进行观察，同时支持浏览器 storage 事件，因此不需要为了语言状态额外引入全局 Provider。

### 扁平化翻译 key

例如 firstBoot.welcome.title 和 profile.save 这样的 key 易于审核、维护和扩展。

### 英语回退

翻译查找顺序为：
1. 当前选择的语言；
2. 英语；
3. 翻译 key 本身。

这样即使某种语言尚未完整翻译，也不会产生空白 UI。

### 原生语言选择器

使用浏览器原生 HTML select，保持键盘和无障碍行为，同时避免增加 UI 依赖。

## 范围边界

本贡献不会尝试翻译：
- 后端动态生成的错误消息；
- 服务名称；
- 产品名称；
- API payload；
- URL；
- 环境变量名称；
- 模型名称；
- 认证语义。

ODS、ODS Talk、Hermes、n8n、Settings、Setup、Owner、Extensions 和 ODS_DEVICE_NAME 等产品及技术标识保持原样。

## 与当前开发工作的兼容性

实现尽量避开目前 Settings 和 FirstBoot 中可能产生冲突的区域。

特别是：
- 保留现有 FirstBoot progress helpers；
- 保留现有 Back 按钮的无障碍属性；
- 不修改 SettingsModal；
- Profile 仍然位于现有的 Dashboard → Settings → Profile 页面。

## 验证

新增测试覆盖：
- 英语默认语言；
- 语言持久化；
- 无效语言回退；
- 西班牙语翻译；
- 简体中文翻译；
- 支持语言列表；
- 语言选择器的持久化和界面更新。

提交 upstream PR 前，还应运行完整的 Dashboard 测试套件。

## Review Checklist

- [ ] 英语仍然是默认语言。
- [ ] 首次启动时西班牙语选择正常。
- [ ] 首次启动时简体中文选择正常。
- [ ] 刷新页面后语言保持不变。
- [ ] Settings → Profile 可以修改语言。
- [ ] 无效语言会回退到英语。
- [ ] 缺少的翻译 key 会回退到英语。
- [ ] FirstBoot 的进度逻辑保持不变。
- [ ] Owner card 流程保持不变。
- [ ] Profile 的姓名和照片功能保持不变。
- [ ] 没有后端/API 行为变化。
- [ ] Dashboard 测试全部通过。
- [ ] git diff --check 通过。
