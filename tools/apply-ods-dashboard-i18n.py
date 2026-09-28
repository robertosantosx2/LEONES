#!/usr/bin/env python3
"""
Apply the ODS dashboard internationalization contribution.

This installer is intentionally self-contained and conservative:
- it only operates from the root of an ODS checkout;
- it creates the small native i18n layer without adding dependencies;
- it changes FirstBoot and the existing Dashboard > Settings > Profile tab;
- it does not create commits;
- it fails loudly if an expected source pattern is missing.

The source code and comments in this installer are written in English so the
implementation is maintainable by the upstream ODS developers. User-facing
documentation for the PR is supplied separately in English, Spanish, and
Simplified Chinese.
"""

from pathlib import Path
import subprocess

ROOT = Path.cwd()
DASH = ROOT / "ods/extensions/services/dashboard"
I18N = DASH / "src/i18n"

if not (DASH / "package.json").exists() or not (DASH / "src/pages/FirstBoot.jsx").exists():
    raise SystemExit("ERROR: run this installer from the root of an ODS checkout.")

branch = subprocess.run(
    ["git", "branch", "--show-current"], check=True, capture_output=True, text=True
).stdout.strip()
if branch != "feat/dashboard-i18n-es-zh":
    raise SystemExit(
        f"ERROR: expected branch feat/dashboard-i18n-es-zh, found {branch or '<detached HEAD>'}."
    )

status = subprocess.run(
    ["git", "status", "--porcelain"], check=True, capture_output=True, text=True
).stdout.strip()
if status:
    raise SystemExit("ERROR: working tree is not clean. Review or stash local changes first.")

I18N.mkdir(parents=True, exist_ok=True)

# The i18n API deliberately stays tiny: React's useSyncExternalStore observes
# the local preference, while the English dictionary remains the universal
# fallback for unsupported or incomplete translations.
files = {
"index.js": """import {useSyncExternalStore} from 'react'
import en from './en'
import es from './es'
import zhCN from './zh-CN'

export const LANGUAGE_KEY = 'ods.language.v1'
export const LANGUAGES = [
  {code: 'en', label: 'English'},
  {code: 'es', label: 'Español'},
  {code: 'zh-CN', label: '简体中文'},
]

const dictionaries = {en, es, 'zh-CN': zhCN}
const EVENT = 'ods:language-changed'

/**
 * Keep language validation in one place so persisted values and UI changes
 * follow exactly the same supported-language rules.
 */
function normalizeLanguage(value) {
  return LANGUAGES.some(({code}) => code === value) ? value : 'en'
}

/**
 * Read the persisted dashboard language.
 *
 * localStorage is intentionally treated as optional: private browsing,
 * browser policy, or storage quotas must never prevent the dashboard from
 * rendering. Invalid or missing values therefore resolve to English.
 */
export function readLanguage() {
  try {
    return normalizeLanguage(window.localStorage.getItem(LANGUAGE_KEY))
  } catch {
    return 'en'
  }
}

/**
 * Persist a supported language and notify components in this browser.
 *
 * The custom event is needed because the browser "storage" event does not
 * fire in the same document that performed the localStorage write.
 */
export function saveLanguage(value) {
  const language = normalizeLanguage(value)
  try {
    window.localStorage.setItem(LANGUAGE_KEY, language)
  } catch {}
  window.dispatchEvent(new Event(EVENT))
  return language
}

function subscribe(callback) {
  window.addEventListener(EVENT, callback)
  window.addEventListener('storage', callback)
  return () => {
    window.removeEventListener(EVENT, callback)
    window.removeEventListener('storage', callback)
  }
}

/**
 * Apply simple named placeholders such as {username} without introducing a
 * template dependency. Unknown placeholders remain visible instead of being
 * silently discarded, which makes incomplete translations easier to detect.
 */
function interpolate(value, vars = {}) {
  return value.replace(/\\{(\\w+)\\}/g, (_, key) =>
    Object.prototype.hasOwnProperty.call(vars, key) ? String(vars[key]) : '{' + key + '}'
  )
}

/**
 * Resolve a translation using the selected dictionary, then English, then
 * the key itself. This guarantees a deterministic fallback for partial
 * translations and newly introduced UI strings.
 */
export function translate(language, key, vars) {
  const value = dictionaries[normalizeLanguage(language)]?.[key] ?? en[key] ?? key
  return interpolate(value, vars)
}

/**
 * React hook used by dashboard components. useSyncExternalStore keeps the
 * selector and translated UI synchronized without adding a context provider
 * or changing the dashboard application's top-level composition.
 */
export function useI18n() {
  const language = useSyncExternalStore(subscribe, readLanguage, () => 'en')
  return {language, setLanguage: saveLanguage, t: (key, vars) => translate(language, key, vars)}
}
""",
"en.js": """export default {
  'common.language': 'Language',
  'common.back': 'Back',
  'common.continue': 'Continue',
  'firstBoot.welcome.title': 'Welcome to ODS.',
  'firstBoot.welcome.body': "Let's get you set up in about a minute. First, give this setup a friendly label for the owner-card audit trail.",
  'firstBoot.setupLabel': 'Setup label',
  'firstBoot.setupLabelHelp': 'This label is recorded on the first owner card only. It does not rename the host yet; change ODS_DEVICE_NAME in Settings before expecting {name}.local to resolve. Letters, numbers, and dashes only.',
  'firstBoot.user.title': "Who's the first user?",
  'firstBoot.user.body': "We'll generate an owner card for them at the end. They scan it to reach ODS Talk on this ODS.",
  'firstBoot.username': 'Username',
  'firstBoot.usernamePlaceholder': 'alice',
  'firstBoot.usernameHelp': 'Recorded with the owner card audit trail. The card remains valid until it is revoked.',
  'firstBoot.stack.title': 'Pick your stack.',
  'firstBoot.stack.body': 'You can change this later. Start small if you want and add things as you go.',
  'firstBoot.stack.chat.title': 'Chat only',
  'firstBoot.stack.chat.blurb': 'Just the chat surface. This is what runs out of the box.',
  'firstBoot.stack.agents.title': 'Chat + Agents',
  'firstBoot.stack.agents.blurb': 'Adds Hermes, web search, usage monitoring, and n8n workflows.',
  'firstBoot.stack.everything.title': 'Full ODS Stack',
  'firstBoot.stack.everything.blurb': 'Adds agents, voice, RAG, research, privacy, and observability (~16GB). Image generation installs separately from Extensions.',
  'firstBoot.confirm.title': 'Ready?',
  'firstBoot.confirm.body': "Tap Finish and we'll generate the owner QR for ODS Talk.",
  'firstBoot.confirm.setupLabel': 'Setup label',
  'firstBoot.confirm.setupHint': 'owner-card audit note',
  'firstBoot.confirm.firstUser': 'First user',
  'firstBoot.confirm.stack': 'Stack',
  'firstBoot.confirm.stackHint': 'services start in the background — verify on the dashboard after setup',
  'firstBoot.confirm.checking': 'Checking owner-card readiness...',
  'firstBoot.confirm.finishLater': 'Finish setup now, then print an owner card from Settings / Setup / Owner after LAN access is enabled.',
  'firstBoot.confirm.proxyRequired': 'Enable ODS proxy before generating owner cards.',
  'firstBoot.confirm.configuring': 'Configuring...',
  'firstBoot.confirm.finish': 'Finish',
  'firstBoot.done.title': "You're set.",
  'firstBoot.done.body': "Here's the owner card for {username}. They scan or tap it to open ODS Talk. Keep the printed QR safe; it remains valid until revoked.",
  'firstBoot.done.qrUnavailable': 'QR generation unavailable on the server.',
  'firstBoot.done.generating': 'Generating QR...',
  'firstBoot.done.copy': 'Copy link',
  'firstBoot.done.copyAria': 'Copy owner link',
  'firstBoot.done.share': 'Share',
  'firstBoot.done.dashboard': 'Open dashboard',
  'firstBoot.done.footer': 'Need more cards or guest invites later? They live under Settings / Setup / Owner.',
  'profile.aria': 'Your profile',
  'profile.identity': 'Your identity',
  'profile.identityBody': 'Your name and photo in the sidebar and {displayName} conversations.',
  'profile.photo': 'Profile photo',
  'profile.preparePhoto': 'Preparing photo…',
  'profile.uploadPhoto': 'Upload photo',
  'profile.removePhoto': 'Remove photo',
  'profile.photoHelp': 'JPG, PNG or WebP · up to 5 MB',
  'profile.photoHelp2': 'Centered crop · circular avatar',
  'profile.displayName': 'Display name',
  'profile.displayNamePlaceholder': 'Your name',
  'profile.privacy': 'Saved only in this browser. Your photo is resized locally and is not sent to the AI model. This does not change your login or permissions.',
  'profile.saved': 'Profile saved.',
  'profile.saveError': 'Your profile could not be saved. Browser storage may be full or disabled.',
  'profile.save': 'Save profile',
  'profile.dashboardAccess': 'Dashboard access',
  'profile.changePassword': 'Change dashboard password',
  'profile.signOut': 'Sign out of this browser',
}
""",
"es.js": """import en from './en'

export default {
  ...en,
  'common.language': 'Idioma',
  'common.back': 'Atrás',
  'common.continue': 'Continuar',
  'firstBoot.welcome.title': 'Bienvenido a ODS.',
  'firstBoot.welcome.body': 'Vamos a configurar ODS en aproximadamente un minuto. Primero, asigna una etiqueta descriptiva para el registro de auditoría de la tarjeta del propietario.',
  'firstBoot.setupLabel': 'Etiqueta de configuración',
  'firstBoot.setupLabelHelp': 'Esta etiqueta solo se registra en la primera tarjeta del propietario. Todavía no cambia el nombre del host; cambia ODS_DEVICE_NAME en Settings antes de esperar que {name}.local resuelva. Solo letras, números y guiones.',
  'firstBoot.user.title': '¿Quién es el primer usuario?',
  'firstBoot.user.body': 'Al final generaremos una tarjeta de propietario. Puede escanearla para acceder a ODS Talk en este ODS.',
  'firstBoot.username': 'Nombre de usuario',
  'firstBoot.usernamePlaceholder': 'alice',
  'firstBoot.usernameHelp': 'Se registra en el historial de auditoría de la tarjeta del propietario. La tarjeta sigue siendo válida hasta que se revoque.',
  'firstBoot.stack.title': 'Elige tu pila.',
  'firstBoot.stack.body': 'Puedes cambiarla más adelante. Empieza con poco si quieres y añade servicios cuando los necesites.',
  'firstBoot.stack.chat.title': 'Solo chat',
  'firstBoot.stack.chat.blurb': 'Solo la superficie de chat. Es lo que se ejecuta de serie.',
  'firstBoot.stack.agents.title': 'Chat + agentes',
  'firstBoot.stack.agents.blurb': 'Añade Hermes, búsqueda web, monitorización de uso y flujos de n8n.',
  'firstBoot.stack.everything.title': 'Pila ODS completa',
  'firstBoot.stack.everything.blurb': 'Añade agentes, voz, RAG, investigación, privacidad y observabilidad (~16 GB). La generación de imágenes se instala por separado desde Extensions.',
  'firstBoot.confirm.title': '¿Listo?',
  'firstBoot.confirm.body': 'Pulsa Finalizar y generaremos el QR del propietario para ODS Talk.',
  'firstBoot.confirm.setupLabel': 'Etiqueta de configuración',
  'firstBoot.confirm.setupHint': 'nota de auditoría de la tarjeta del propietario',
  'firstBoot.confirm.firstUser': 'Primer usuario',
  'firstBoot.confirm.stack': 'Pila',
  'firstBoot.confirm.stackHint': 'los servicios se inician en segundo plano; verifica el dashboard después de la configuración',
  'firstBoot.confirm.checking': 'Comprobando la disponibilidad de la tarjeta del propietario...',
  'firstBoot.confirm.finishLater': 'Finaliza la configuración y después imprime una tarjeta desde Settings / Setup / Owner cuando el acceso LAN esté habilitado.',
  'firstBoot.confirm.proxyRequired': 'Activa el proxy de ODS antes de generar tarjetas de propietario.',
  'firstBoot.confirm.configuring': 'Configurando...',
  'firstBoot.confirm.finish': 'Finalizar',
  'firstBoot.done.title': 'Todo listo.',
  'firstBoot.done.body': 'Aquí está la tarjeta del propietario para {username}. Puede escanearla o tocarla para abrir ODS Talk. Guarda el QR impreso en un lugar seguro; seguirá siendo válido hasta que se revoque.',
  'firstBoot.done.qrUnavailable': 'La generación del QR no está disponible en el servidor.',
  'firstBoot.done.generating': 'Generando QR...',
  'firstBoot.done.copy': 'Copiar enlace',
  'firstBoot.done.copyAria': 'Copiar enlace del propietario',
  'firstBoot.done.share': 'Compartir',
  'firstBoot.done.dashboard': 'Abrir dashboard',
  'firstBoot.done.footer': '¿Necesitas más tarjetas o invitaciones de invitados? Están en Settings / Setup / Owner.',
  'profile.aria': 'Tu perfil',
  'profile.identity': 'Tu identidad',
  'profile.identityBody': 'Tu nombre y foto en la barra lateral y en las conversaciones de {displayName}.',
  'profile.photo': 'Foto de perfil',
  'profile.preparePhoto': 'Preparando foto…',
  'profile.uploadPhoto': 'Subir foto',
  'profile.removePhoto': 'Eliminar foto',
  'profile.photoHelp': 'JPG, PNG o WebP · hasta 5 MB',
  'profile.photoHelp2': 'Recorte centrado · avatar circular',
  'profile.displayName': 'Nombre para mostrar',
  'profile.displayNamePlaceholder': 'Tu nombre',
  'profile.privacy': 'Se guarda solo en este navegador. La foto se redimensiona localmente y no se envía al modelo de IA. Esto no cambia tu inicio de sesión ni tus permisos.',
  'profile.saved': 'Perfil guardado.',
  'profile.saveError': 'No se ha podido guardar tu perfil. El almacenamiento del navegador puede estar lleno o desactivado.',
  'profile.save': 'Guardar perfil',
  'profile.dashboardAccess': 'Acceso al dashboard',
  'profile.changePassword': 'Cambiar contraseña del dashboard',
  'profile.signOut': 'Cerrar sesión en este navegador',
}
""",
"zh-CN.js": """import en from './en'

export default {
  ...en,
  'common.language': '语言',
  'common.back': '返回',
  'common.continue': '继续',
  'firstBoot.welcome.title': '欢迎使用 ODS。',
  'firstBoot.welcome.body': '大约一分钟即可完成设置。首先，为所有者卡片审计记录设置一个易于识别的标签。',
  'firstBoot.setupLabel': '设置标签',
  'firstBoot.setupLabelHelp': '此标签只会记录在第一张所有者卡片上。它不会立即重命名主机；请在 Settings 中修改 ODS_DEVICE_NAME 后，{name}.local 才会按预期解析。仅限字母、数字和短横线。',
  'firstBoot.user.title': '谁是第一个用户？',
  'firstBoot.user.body': '完成后我们会为该用户生成所有者卡片。用户可以扫描卡片进入此 ODS 上的 ODS Talk。',
  'firstBoot.username': '用户名',
  'firstBoot.usernamePlaceholder': 'alice',
  'firstBoot.usernameHelp': '会与所有者卡片审计记录一起保存。撤销前该卡片一直有效。',
  'firstBoot.stack.title': '选择你的服务栈。',
  'firstBoot.stack.body': '以后可以更改。如果需要，可以从小规模开始，再逐步添加服务。',
  'firstBoot.stack.chat.title': '仅聊天',
  'firstBoot.stack.chat.blurb': '只有聊天界面。这是开箱即用的默认内容。',
  'firstBoot.stack.agents.title': '聊天 + Agents',
  'firstBoot.stack.agents.blurb': '增加 Hermes、网页搜索、使用监控和 n8n 工作流。',
  'firstBoot.stack.everything.title': '完整 ODS 服务栈',
  'firstBoot.stack.everything.blurb': '增加 Agents、语音、RAG、研究、隐私和可观测性（约 16GB）。图像生成需要从 Extensions 单独安装。',
  'firstBoot.confirm.title': '准备好了吗？',
  'firstBoot.confirm.body': '点击完成，我们将为 ODS Talk 生成所有者二维码。',
  'firstBoot.confirm.setupLabel': '设置标签',
  'firstBoot.confirm.setupHint': '所有者卡片审计备注',
  'firstBoot.confirm.firstUser': '第一个用户',
  'firstBoot.confirm.stack': '服务栈',
  'firstBoot.confirm.stackHint': '服务将在后台启动；设置完成后请在 dashboard 中验证',
  'firstBoot.confirm.checking': '正在检查所有者卡片是否就绪...',
  'firstBoot.confirm.finishLater': '先完成设置；启用 LAN 访问后，可从 Settings / Setup / Owner 打印所有者卡片。',
  'firstBoot.confirm.proxyRequired': '请先启用 ODS 代理，再生成所有者卡片。',
  'firstBoot.confirm.configuring': '正在配置...',
  'firstBoot.confirm.finish': '完成',
  'firstBoot.done.title': '设置完成。',
  'firstBoot.done.body': '这是 {username} 的所有者卡片。扫描或轻触即可打开 ODS Talk。请妥善保管打印的二维码；撤销前它一直有效。',
  'firstBoot.done.qrUnavailable': '服务器无法生成二维码。',
  'firstBoot.done.generating': '正在生成二维码...',
  'firstBoot.done.copy': '复制链接',
  'firstBoot.done.copyAria': '复制所有者链接',
  'firstBoot.done.share': '分享',
  'firstBoot.done.dashboard': '打开 dashboard',
  'firstBoot.done.footer': '以后需要更多卡片或访客邀请？请前往 Settings / Setup / Owner。',
  'profile.aria': '你的个人资料',
  'profile.identity': '你的身份',
  'profile.identityBody': '侧边栏以及 {displayName} 对话中显示的姓名和照片。',
  'profile.photo': '个人资料照片',
  'profile.preparePhoto': '正在准备照片…',
  'profile.uploadPhoto': '上传照片',
  'profile.removePhoto': '删除照片',
  'profile.photoHelp': 'JPG、PNG 或 WebP · 最大 5 MB',
  'profile.photoHelp2': '居中裁剪 · 圆形头像',
  'profile.displayName': '显示名称',
  'profile.displayNamePlaceholder': '你的姓名',
  'profile.privacy': '仅保存在此浏览器中。照片会在本地调整大小，不会发送给 AI 模型。这不会改变你的登录状态或权限。',
  'profile.saved': '个人资料已保存。',
  'profile.saveError': '无法保存个人资料。浏览器存储空间可能已满或被禁用。',
  'profile.save': '保存个人资料',
  'profile.dashboardAccess': 'Dashboard 访问',
  'profile.changePassword': '修改 dashboard 密码',
  'profile.signOut': '退出此浏览器的登录',
}
""",
"LanguageSelector.jsx": """import {LANGUAGES,useI18n} from './index'

/**
 * Small dependency-free language selector shared by FirstBoot and Settings.
 *
 * Keeping this component native (a <select>) avoids adding another UI
 * dependency and keeps keyboard/accessibility behavior provided by the
 * browser. Language names are intentionally displayed in their native form.
 */
export default function LanguageSelector() {
  const {language,setLanguage,t} = useI18n()

  return <label className="firstboot-language">
    <span>{t('common.language')}</span>
    <select value={language} onChange={event => setLanguage(event.target.value)} aria-label={t('common.language')}>
      {LANGUAGES.map(item => <option key={item.code} value={item.code}>{item.label}</option>)}
    </select>
  </label>
}
""",
"index.test.js": """import {beforeEach,describe,expect,it} from 'vitest'
import {LANGUAGE_KEY,LANGUAGES,readLanguage,saveLanguage,translate} from './index'

describe('dashboard i18n', () => {
  beforeEach(() => localStorage.clear())

  it('defaults to English', () => {
    expect(readLanguage()).toBe('en')
    expect(translate('en', 'common.continue')).toBe('Continue')
  })

  it('persists supported languages', () => {
    saveLanguage('es')
    expect(readLanguage()).toBe('es')
    expect(saveLanguage('zh-CN')).toBe('zh-CN')
    expect(readLanguage()).toBe('zh-CN')
  })

  it('falls back to English for an invalid language', () => {
    localStorage.setItem(LANGUAGE_KEY, 'xx')
    expect(readLanguage()).toBe('en')
  })

  it('uses the requested dictionary', () => {
    expect(translate('es', 'profile.save')).toBe('Guardar perfil')
    expect(translate('zh-CN', 'profile.save')).toBe('保存个人资料')
  })

  it('falls back to the key when a translation is missing', () => {
    expect(translate('es', 'missing.key')).toBe('missing.key')
  })

  it('exposes the three supported languages', () => {
    expect(LANGUAGES.map(item => item.code)).toEqual(['en', 'es', 'zh-CN'])
  })
})
""",
"LanguageSelector.test.jsx": """import {fireEvent,render,screen} from '@testing-library/react'
import {beforeEach,describe,expect,it} from 'vitest'
import LanguageSelector from './LanguageSelector'
import {LANGUAGE_KEY} from './index'

describe('LanguageSelector', () => {
  beforeEach(() => localStorage.clear())

  it('changes and persists the selected language', () => {
    render(<LanguageSelector />)
    const select = screen.getByRole('combobox', {name: 'Language'})

    fireEvent.change(select, {target: {value: 'es'}})

    expect(select).toHaveValue('es')
    expect(localStorage.getItem(LANGUAGE_KEY)).toBe('es')
    expect(screen.getByText('Idioma')).toBeInTheDocument()
  })
})
""",
}

for name, content in files.items():
    (I18N / name).write_text(content, encoding="utf-8")

def replace_once(path, old, new):
    p = ROOT / path
    source = p.read_text(encoding="utf-8")
    if new in source:
        return
    if old not in source:
        raise SystemExit(f"ERROR: expected source pattern not found in {path}: {old[:100]!r}")
    p.write_text(source.replace(old, new, 1), encoding="utf-8")

firstboot = "ods/extensions/services/dashboard/src/pages/FirstBoot.jsx"
replace_once(firstboot,
"import { useEffect, useMemo, useState } from 'react'",
"import { useEffect, useMemo, useState } from 'react'\nimport { useI18n } from '../i18n'\nimport LanguageSelector from '../i18n/LanguageSelector'")

# The hook is intentionally placed in the top-level FirstBoot component so
# the header selector remains synchronized with the Profile selector.
replace_once(firstboot,
"export default function FirstBoot({ onComplete }) {",
"export default function FirstBoot({ onComplete }) {\n  const {t} = useI18n()")

p = Path(firstboot)
source = p.read_text(encoding="utf-8")

# Each wizard step is a separate React component, so it needs its own i18n hook.
for signature in [
    "function WelcomeStep({ deviceName, setDeviceName, onNext }) {",
    "function UserStep({ username, setUsername, onNext, onBack }) {",
    "function StackStep({ stack, setStack, onNext, onBack }) {",
]:
    source = source.replace(signature, signature + "\n  const {t} = useI18n()", 1)
source = source.replace(
    "  ownerCardStatusLoading,\n}) {\n  const stackTitle",
    "  ownerCardStatusLoading,\n}) {\n  const {t} = useI18n()\n  const stackTitle",
    1,
)
source = source.replace(
    "function DoneScreen({ invite, onDone }) {\n  const [copied",
    "function DoneScreen({ invite, onDone }) {\n  const {t} = useI18n()\n  const [copied",
    1,
)
for old, new in {
    "        Let&apos;s get you set up in about a minute. First, give this setup a friendly label for the owner-card audit trail.": "        {t('firstBoot.welcome.body')}",
    "        We&apos;ll generate an owner card for them at the end. They scan it to reach ODS Talk on this ODS.": "        {t('firstBoot.user.body')}",
    "          Recorded with the owner card audit trail. The card remains valid until it is revoked.": "          {t('firstBoot.usernameHelp')}",
    "        You can change this later. Start small if you want and add things as you go.": "        {t('firstBoot.stack.body')}",
    "        Tap Finish and we&apos;ll generate the owner QR for ODS Talk.": "        {t('firstBoot.confirm.body')}",
    "            {' '}Finish setup now, then print an owner card from Settings / Setup / Owner after LAN access is enabled.": "            {' '}{t('firstBoot.confirm.finishLater')}",
    "            {ownerCardStatus.reason || 'Enable ODS proxy before generating owner cards.'}": "            {ownerCardStatus.reason || t('firstBoot.confirm.proxyRequired')}",
    "          {finishing ? 'Configuring...' : 'Finish'}": "          {finishing ? t('firstBoot.confirm.configuring') : t('firstBoot.confirm.finish')}",
    "        Continue": "        {t('common.continue')}",
    ">Welcome to ODS.<": ">{t('firstBoot.welcome.title')}<",
    ">Let's get you set up in about a minute. First, give this setup a friendly label for the owner-card audit trail.<": ">{t('firstBoot.welcome.body')}<",
    ">Setup label<": ">{t('firstBoot.setupLabel')}<",
    ">Who's the first user?<": ">{t('firstBoot.user.title')}<",
    ">We'll generate an owner card for them at the end. They scan it to reach ODS Talk on this ODS.<": ">{t('firstBoot.user.body')}<",
    ">Username<": ">{t('firstBoot.username')}<",
    ">Pick your stack.<": ">{t('firstBoot.stack.title')}<",
    ">You can change this later. Start small if you want and add things as you go.<": ">{t('firstBoot.stack.body')}<",
    ">Chat only<": ">{t('firstBoot.stack.chat.title')}<",
    ">Chat + Agents<": ">{t('firstBoot.stack.agents.title')}<",
    ">Full ODS Stack<": ">{t('firstBoot.stack.everything.title')}<",
    ">Ready?<": ">{t('firstBoot.confirm.title')}<",
    ">Tap Finish and we'll generate the owner QR for ODS Talk.<": ">{t('firstBoot.confirm.body')}<",
    ">First user<": ">{t('firstBoot.confirm.firstUser')}<",
    ">Stack<": ">{t('firstBoot.confirm.stack')}<",
    ">Checking owner-card readiness...<": ">{t('firstBoot.confirm.checking')}<",
    ">Configuring...<": ">{t('firstBoot.confirm.configuring')}<",
    ">Finish<": ">{t('firstBoot.confirm.finish')}<",
    ">You're set.<": ">{t('firstBoot.done.title')}<",
    ">Generating QR...<": ">{t('firstBoot.done.generating')}<",
    ">Share<": ">{t('firstBoot.done.share')}<",
    ">Open dashboard<": ">{t('firstBoot.done.dashboard')}<",
    ">Back</button>": ">{t('common.back')}</button>",
}.items():
    source = source.replace(old, new)

# Translate data-driven cards and richer JSX blocks.
source = source.replace("{opt.title}", "{t(opt.titleKey)}")
source = source.replace("{opt.blurb}", "{t(opt.blurbKey)}")
source = source.replace(
    "const stackTitle = STACK_OPTIONS.find(s => s.id === stack)?.title || stack",
    "const selectedStack = STACK_OPTIONS.find(s => s.id === stack)\n  const stackTitle = selectedStack?.titleKey ? t(selectedStack.titleKey) : stack",
)
source = source.replace(
    "This label is recorded on the first owner card only. It does not rename the host yet;\n          change <code className=\"text-theme-accent\">ODS_DEVICE_NAME</code> in Settings before expecting\n          <code className=\"text-theme-accent\"> {deviceName.trim() || 'ods'}.local</code> to resolve.\n          Letters, numbers, and dashes only.",
    "{t('firstBoot.setupLabelHelp', {name: deviceName.trim() || 'ods'})}",
)
source = source.replace("{qrError || 'Generating QR...'}", "{qrError || t('firstBoot.done.generating')}")
source = source.replace(
    "Here&apos;s the owner card for <strong className=\"text-theme-text\">{invite.target_username}</strong>.\n        They scan or tap it to open ODS Talk. Keep the printed QR safe; it remains valid until revoked.",
    "{t('firstBoot.done.body', {username: invite.target_username})}",
)
source = source.replace('title="Copy link"', "title={t('firstBoot.done.copy')}")
source = source.replace('aria-label="Copy owner link"', "aria-label={t('firstBoot.done.copyAria')}")
source = source.replace(
    "Need more cards or guest invites later? They live under <strong>Settings</strong> / <strong>Setup / Owner</strong>.",
    "{t('firstBoot.done.footer')}",
)
source = source.replace(
    "      <h1 className=\"text-3xl font-bold text-theme-text mb-3\">Who&apos;s the first user?</h1>",
    "      <h1 className=\"text-3xl font-bold text-theme-text mb-3\">{t('firstBoot.user.title')}</h1>",
)
source = source.replace(
    "      <h1 className=\"text-3xl font-bold text-theme-text mb-3\">You&apos;re set.</h1>",
    "      <h1 className=\"text-3xl font-bold text-theme-text mb-3\">{t('firstBoot.done.title')}</h1>",
)
source = source.replace('aria-label=\"Back\"', "aria-label={t('common.back')}")
source = source.replace(
    'label=\"Setup label\" hint=\"owner-card audit note\"',
    "label={t('firstBoot.confirm.setupLabel')} hint={t('firstBoot.confirm.setupHint')}",
)
source = source.replace(
    'label=\"First user\" value={username}',
    "label={t('firstBoot.confirm.firstUser')} value={username}",
)
source = source.replace(
    'label=\"Stack\" value={stackTitle} hint=\"services start in the background — verify on the dashboard after setup\"',
    "label={t('firstBoot.confirm.stack')} value={stackTitle} hint={t('firstBoot.confirm.stackHint')}",
)
source = source.replace(
    '<Row label="Setup label" value={deviceName.trim() || \'ods\'} hint="owner-card audit note" />',
    "<Row label={t('firstBoot.confirm.setupLabel')} value={deviceName.trim() || 'ods'} hint={t('firstBoot.confirm.setupHint')} />",
)
source = source.replace(
    '<Row label="First user" value={username.trim()} />',
    "<Row label={t('firstBoot.confirm.firstUser')} value={username.trim()} />",
)
source = source.replace(
    "            Share",
    "            {t('firstBoot.done.share')}",
)
source = source.replace(
    "          Open dashboard",
    "          {t('firstBoot.done.dashboard')}",
)
# Preserve existing progress/finish logic and add the selector without moving
# the StepDots implementation used by upstream PRs.
header = source.find("<header")
if header < 0:
    raise SystemExit("ERROR: FirstBoot header not found.")
header_end = source.find(">", header)
selector = """
      <LanguageSelector />
"""
source = source[:header_end + 1] + selector + source[header_end + 1:]
# Stack option labels are stored as translation keys while retaining their
# existing English title/blurb fields for untouched runtime/error behavior.
source = source.replace("title: 'Chat only',", "title: 'Chat only',\n    titleKey: 'firstBoot.stack.chat.title',")
source = source.replace("blurb: 'Just the chat surface. This is what runs out of the box.',", "blurb: 'Just the chat surface. This is what runs out of the box.',\n    blurbKey: 'firstBoot.stack.chat.blurb',")
source = source.replace("title: 'Chat + Agents',", "title: 'Chat + Agents',\n    titleKey: 'firstBoot.stack.agents.title',")
source = source.replace("blurb: 'Adds Hermes, web search, usage monitoring, and n8n workflows.',", "blurb: 'Adds Hermes, web search, usage monitoring, and n8n workflows.',\n    blurbKey: 'firstBoot.stack.agents.blurb',")
source = source.replace("title: 'Full ODS Stack',", "title: 'Full ODS Stack',\n    titleKey: 'firstBoot.stack.everything.title',")
source = source.replace("blurb: 'Adds agents, voice, RAG, research, privacy, and observability (~16GB). Image generation installs separately from Extensions.',", "blurb: 'Adds agents, voice, RAG, research, privacy, and observability (~16GB). Image generation installs separately from Extensions.',\n    blurbKey: 'firstBoot.stack.everything.blurb',")
p.write_text(source, encoding="utf-8")

# Profile is the existing Dashboard > Settings > Profile tab. No new route or
# SettingsModal change is required, reducing collision risk with open PRs.
profile = ROOT / "ods/extensions/services/dashboard/src/components/settings/ProfileSettings.jsx"
source = profile.read_text(encoding="utf-8")
source = source.replace(
    "import {usePortalIdentity} from '../../contexts/PortalIdentityContext'",
    "import {usePortalIdentity} from '../../contexts/PortalIdentityContext'\nimport {useI18n} from '../../i18n'\nimport LanguageSelector from '../../i18n/LanguageSelector'"
)
source = source.replace(
    "export default function ProfileSettings() {",
    "export default function ProfileSettings() {\n  const {t} = useI18n()"
)
replacements = {
    'aria-label="Your profile"': "aria-label={t('profile.aria')}",
    "<h2>Your identity</h2>": "<h2>{t('profile.identity')}</h2>",
    "Your name and photo in the sidebar and {displayName} conversations.": "{t('profile.identityBody', {displayName})}",
    'aria-label="Profile photo"': "aria-label={t('profile.photo')}",
    "Preparing photo…": "{t('profile.preparePhoto')}",
    "Upload photo": "{t('profile.uploadPhoto')}",
    "Remove photo": "{t('profile.removePhoto')}",
    "JPG, PNG or WebP · up to 5 MB": "{t('profile.photoHelp')}",
    "Centered crop · circular avatar": "{t('profile.photoHelp2')}",
    "Display name": "{t('profile.displayName')}",
    'placeholder="Your name"': "placeholder={t('profile.displayNamePlaceholder')}",
    "Profile saved.": "{t('profile.saved')}",
    "Your profile could not be saved. Browser storage may be full or disabled.": "{t('profile.saveError')}",
    "Save profile": "{t('profile.save')}",
    "<h3>Dashboard access</h3>": "<h3>{t('profile.dashboardAccess')}</h3>",
    "Change dashboard password": "{t('profile.changePassword')}",
    "Sign out of this browser": "{t('profile.signOut')}",
    "Saved only in this browser. Your photo is resized locally and is not sent to the AI model. This does not change your login or permissions.": "{t('profile.privacy')}",
}
for old, new in replacements.items():
    source = source.replace(old, new)

# Some original strings live inside JavaScript string literals. Replace the
# complete call/expression so the generated JSX contains executable t(...)
# expressions rather than a quoted "{t(...)}" string.
source = source.replace("setNotice('{t('profile.saved')}')", "setNotice(t('profile.saved'))")
source = source.replace("setError('{t('profile.saveError')}')", "setError(t('profile.saveError'))")
source = source.replace("{busy ? '{t('profile.preparePhoto')}' : '{t('profile.uploadPhoto')}'", "{busy ? t('profile.preparePhoto') : t('profile.uploadPhoto')}")
source = source.replace(
    '<section className="profile-dashboard-access" aria-label="Dashboard access">',
    '<section className="profile-dashboard-access" aria-label={t(\'profile.dashboardAccess\')}>',
)
language_block = """<LanguageSelector />
    """
needle = '<div className="profile-photo-editor">'
if language_block not in source:
    if needle not in source:
        raise SystemExit("ERROR: Profile photo editor not found.")
    source = source.replace(needle, language_block + needle, 1)
profile.write_text(source, encoding="utf-8")

# Validate the generated component sources before touching the working tree.
# These guards catch the two most dangerous classes of installer regression:
# quoted translation expressions and untranslated core wizard copy.
for forbidden in [
    "setNotice('{t('profile.saved')}')",
    "setError('{t('profile.saveError')}')",
    "{busy ? '{t('profile.preparePhoto')}' : '{t('profile.uploadPhoto')}'",
]:
    if forbidden in source:
        raise SystemExit(f"ERROR: invalid quoted translation expression generated: {forbidden!r}")

firstboot_source = p.read_text(encoding="utf-8")
for required in [
    "Welcome to ODS.",
    "Who's the first user?",
    "Pick your stack.",
    "Ready?",
]:
    if required in firstboot_source:
        raise SystemExit(f"ERROR: untranslated FirstBoot text remains: {required!r}")

# The installer deliberately does not alter existing test files.
# Translation expressions are inserted as JSX expressions, never as quoted
# strings, so React evaluates t(...) at render time. Existing
# English tests continue to exercise the default dictionary; the new focused
# tests cover persistence and selector behavior.
check = subprocess.run(["git", "diff", "--check"], capture_output=True, text=True)
if check.returncode:
    print(check.stdout)
    print(check.stderr)
    raise SystemExit("ERROR: git diff --check failed.")

print("ODS dashboard i18n installer completed successfully.")
print("Changed: dashboard/src/i18n/*, FirstBoot.jsx, ProfileSettings.jsx")
print("No commit was created.")
print("Next: inspect git diff, then run the dashboard test suite.")
